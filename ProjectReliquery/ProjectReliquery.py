#!/usr/bin/env python3

import requests
import argparse
from datetime import datetime, timedelta
import time
import json
import sys
import inspect
import logging
import traceback
import os


#Class that has IT row properties.
class IT_Row(object):
    color_list = [5,8,9]
    color_file_path = '.color_data.txt'
    color_map = {}
    color_index = 1

    """Init Constructor"""
    def __init__(self, hire_date=None, first_name=None, last_name=None, title=None, office=None, pmail=None, row_id=None):
        #Init Delcaration.
        self.hire_date = hire_date
        self.first_name = first_name
        self.last_name = last_name
        self.title = title
        self.office = office
        self.pmail = pmail
        self.row_id = row_id

    #This formats the object for post request to update fields.
    def to_json(self):
        color = self.colorizer(self.hire_date)
        return [{       
            "format": f",,,,,,2,,,{color},,,,,,", #Format string.
            "cells": [
            {"columnId": "*exampleColumnId*", "value": self.hire_date}, #IT Sheet ColumnIds.
            { "columnId": "*exampleColumnId*", "value": self.first_name},
            { "columnId": "*exampleColumnId*", "value": self.last_name},
            { "columnId": "*exampleColumnId*", "value": self.title},
            { "columnId": "*exampleColumnId*", "value": self.office},
            { "columnId": "*exampleColumnId*", "value": self.pmail}
            ]
        }]

    #This determines colors on row creation by reading the hidden .color_data.txt file.
    def load_color_data(cls):
        try:
            with open(cls.color_file_path, 'r') as file:
                data = file.read().strip().split(',')
                color_id = int(data[0])
                last_hire_date = data[1]
                future_hire_date = data[2]
                return color_id, last_hire_date, future_hire_date
        except (FileNotFoundError, ValueError, IndexError):
            return 0, '', ''

    #Writes color data to file for persistence. 
    def save_color_data(cls, color_id, last_hire_date, future_hire_date):
        with open(cls.color_file_path, 'w') as file:
            file.write(f"{color_id},{last_hire_date},{future_hire_date}")

    #Sets the color for the row being created.
    def colorizer(cls, hire_date):
        current_color_id, last_hire_date, future_hire_date = cls.load_color_data()

        # Check if the hire_date is greater than the last processed hire_date
        if hire_date != last_hire_date:
            last_hire_date = hire_date
            current_color_id = (current_color_id + 1) % len(cls.color_list)

        if hire_date > future_hire_date:
            future_hire_date = hire_date

        cls.save_color_data(current_color_id, last_hire_date, future_hire_date)

        return cls.color_list[current_color_id]

#Checks input arguments
def argument_checker():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-a", "--apikey", type = str, required = False, help = "Add API Key")
    argParser.add_argument("-f", "--keyfile", type = str, required = False, help = "File storing API key")
    argParser.add_argument("-d", "--debug", action="store_true", required = False, help = "Enables debug logging")
    argParser.add_argument("-v", "--verbose", action="store_true", required = False, help = "Enables verbose printing")

    args = argParser.parse_args()
    return args

#Checks four conditions of API key possibilities. Could potentially upgrade this to use keyring?
def check_api_key():
    #Checks for -a arg.
    args = argument_checker()
    if args.apikey:
        return args.apikey

    #Checks for -o arg.
    if args.keyfile:
        keyfile_path = args.keyfile
        if not keyfile_path.endswith('.txt'):
            keyfile_path += '.txt'
        try:
            with open(keyfile_path, 'r') as file:
                return file.read().strip()
        except FileNotFoundError:
            pass
    #Checks for file named key.txt.
    try:
        with open('key.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        pass

    #Asks user for API key input manually.
    return input("Enter API key: ")

#Sets up logging for the script.
def configure_logging():
    args = argument_checker()
    if args.debug:
        # Debug mode configuration: Show all requests' info
        logging.basicConfig(filename = 'reliquery.debug', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode = 'w')
    else:
        # Production mode configuration: Log only error messages
        logging.basicConfig(filename = 'reliquery.latest.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', filemode = 'w')
        logging.basicConfig(filename = 'reliquery.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', filemode = 'a')

#Sends a http GET request to the sheet.
def pull_data(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        log_debug_info(response, name = "pull_data function")
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        return None

#Sends a http GET request for a specific row of the sheet.
def pull_row_data(api_url, headers, row_id):
    api_url = f"{api_url}/rows/{row_id}"
    try:
        response = requests.get(api_url, headers=headers)
        log_debug_info(response, row_id = row_id, name = "pull_row_data function")
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        return None

#Sends a http POST request to create a new row.
def create_row(api_url, headers, data):
    api_url = f"{api_url}/rows"
    try:
        response = requests.post(api_url, headers=headers, json=data)
        log_debug_info(response, data = data, name = "create_row function")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        return None

#Sends a http PUT request to update all elements in a row.
def update_row(api_url, headers, data, row_id):
    api_url = f"{api_url}/rows/{row_id}"
    try:
        response = requests.put(api_url, headers = headers, json = data)
        log_debug_info(response, row_id = row_id, data = data, name = "update_row function")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        return None

#Sends a http DELETE request to delete a row.
def delete_row(api_url, headers, params):
    try:
        deletion_url = f"{api_url}/rows?ids={params}"
        response = requests.delete(deletion_url, headers = headers, data = "")
        log_debug_info(response, row_id = params, name = "delete_row function")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")

#Sends a http POST request to move a row from one sheet to another.
#This is used to maintain data integrity and make sure things don't get lost.
def archive_row(api_url, headers, row_id):
    try:
        archive_url = f"{api_url}/rows/move"
        #The sheetID referenced in the next statement is the archive sheet
        payload = json.dumps({"rowIds" : [row_id], "to" : {"sheetId" : "*exampleColumnId*"}}) #Archive sheet id
        response = requests.post(archive_url, headers = headers, data = payload)
        log_debug_info(response, row_id = row_id, name = "archive_row function")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")

#Sends a http POST request have rows be sorted by specific columns.
def sort_rows(api_url, headers):
    api_url = f"{api_url}/sort"
    data = json.dumps({
        "sortCriteria": [
        {
          "columnId": "*exampleColumnId*", #Hire date
          "direction": "DESCENDING"
        },
        { "columnId": "*exampleColumnId*", #Title
          "direction": "DESCENDING"
        },
        { "columnId": "*exampleColumnId*", #First name
          "direction": "ASCENDING"
        }
      ]
    })

    try:
        response = requests.post(api_url, headers=headers, data=data)
        log_debug_info(response, data = data, name = "sort_rows function")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")

#Moves old IT rows to the archive sheet
def archive_old_it_rows(api_url, headers, old_rows):
    for row in old_rows:
        archive_row(api_url, headers, row.row_id)

#Compares the hire dates for HR and IT. If they don't match, IT will adopt the HR date.
def replace_mismatched_dates(api_url, headers, valid_hr_rows, valid_it_rows):
    both_lists_emails = set(hr_row.pmail for hr_row in valid_hr_rows) & set(it_row.pmail for it_row in valid_it_rows)
    for email in both_lists_emails:
        hr_row = next(hr_row for hr_row in valid_hr_rows if hr_row.pmail == email)
        it_row = next(it_row for it_row in valid_it_rows if it_row.pmail == email)     
        if hr_row.hire_date != it_row.hire_date:

            payload = {
              "cells": [
                {
                  "columnId": "*exampleColumnId*",#hire date column id
                  "value": hr_row.hire_date 
                }
              ]
            }

            update_row(api_url, headers, payload, it_row.row_id)

#It is messy but I just can't deal with the colors anymore.
#If one row has it's color changed doesn't have the same color as the rest that share a date, it will adopt the color of the majority for that date.
def update_colors_for_it_rows(api_url, headers, valid_it_rows):
    ids_to_colors, date_color_count_dict = get_all_rows_color(api_url, headers)
    for it_row in valid_it_rows:
        current_color = ids_to_colors.get(it_row.row_id, None)
        highest_color = get_highest_color(date_color_count_dict, it_row.hire_date)

        if current_color != highest_color:
            updated_color = highest_color
            row_to_fix = pull_row_data(api_url, headers, it_row.row_id)

            cell_list = [
                    {
                        "columnId" : cell['columnId'],
                        "value" : cell['value'] if cell.get('value') else "",
                        "format" : f",,,,,,2,,,{updated_color},,,,,,",
                        "strict": "false"
                    }
                for cell in row_to_fix['cells']
                ]

            payload = {"cells" : cell_list}
            update_row(api_url, headers, payload, it_row.row_id)

#Datetime helper for figuring out when to set cutoffs for dates on sheets.
def date_calculations(data):
    json_dt = datetime.strptime(data, '%Y-%m-%d')
    # Get the current datetime
    current_dt = datetime.now()
    # Calculate the time difference
    time_difference = current_dt - json_dt
    return time_difference

#Helper to find the value of a specific cell
def find_value_by_column_id(row, column_id, format_mode = False):
    for cell in row:
        if cell['columnId'] == int(column_id):
            try:
                if format_mode:
                    return cell['format']
                return cell['value']
            except KeyError:
                return None
    return None

#Logging function
def log_debug_info(response, row_id=None, name=None, data=None):

    if row_id is not None:
        logging.debug(f"Row id: {row_id}")
    if name is not None:
        logging.debug(f"Name: {name}")
    if data is not None:
        logging.debug(f"Data: {data}")
    if response is not None:
        logging.debug(f"Response Status: {response.status_code}")

    logging.debug(f"Traceback: {traceback.format_exc()}")

    args = argument_checker()
    if args.verbose:
        print(f"Response Status: {response.status_code}")

#Color helper functions
def generate_date_color_count(rows_with_dates_colors):
    date_color_count_dict = {}

    for row_data in rows_with_dates_colors:
        date = row_data['date']
        color = row_data['color']

        if date not in date_color_count_dict:
            date_color_count_dict[date] = {}

        if color in date_color_count_dict[date]:
            date_color_count_dict[date][color] += 1
        else:
            date_color_count_dict[date][color] = 1

    return date_color_count_dict

def get_highest_color(date_color_count_dict, date):
    if date in date_color_count_dict:
        color_count = date_color_count_dict[date]
        highest_color = max(color_count, key=color_count.get, default=None)
        return highest_color
    else:
        return None

def get_all_rows_color(api_url, headers):
    color_map = {}
    ids_to_colors = {}
    api_url += "?include=format"
    it_data = pull_data(api_url, headers)

    rows_with_dates_colors = [
        {
            'date': find_value_by_column_id(row['cells'], '*exampleColumnId*'), #date
            'color': [value for value in find_value_by_column_id(row['cells'], '*exampleColumnId*', True).split(',') if value][-1], #date
            'id': row['id']
        }
        for row in it_data['rows']
        if find_value_by_column_id(row['cells'], '*exampleColumnId*') #pmail exists
    ]

    date_color_count_dict = generate_date_color_count(rows_with_dates_colors)
    for obj in rows_with_dates_colors:
        ids_to_colors[obj['id']] = obj['color']
    return ids_to_colors, date_color_count_dict

#Grabs all the rows from the HR sheet and turns them into IT_Row objects
def clean_data_based_on_dates_hr(data):
    rows_to_add = [
        IT_Row(
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Date
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #First
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Last
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Title
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Office
            find_value_by_column_id(row['cells'], '*exampleColumnId*') #pmail
        )
        for row in data['rows']
        #if pmail and date has not passed
        if find_value_by_column_id(row['cells'], '*exampleColumnId*') and date_calculations(find_value_by_column_id(row['cells'], '*exampleColumnId*')) < timedelta(days=0)
    ]
    return rows_to_add

#Grabs all the rows from the IT sheet and turns them into IT_Row objects
def clean_data_based_on_dates_it(data, return_need_to_delete = False):
    objects = [
        IT_Row(
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Date
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #First
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Last
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Title
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #Office
            find_value_by_column_id(row['cells'], '*exampleColumnId*'), #pmail
            row['id']
        )
            for row in data['rows']
            if find_value_by_column_id(row['cells'], '*exampleColumnId*')
        ]
        
    rows_to_add = [row for row in objects if date_calculations(row.hire_date) < timedelta(days=0)]
    if return_need_to_delete:
        old_rows = [row for row in objects if date_calculations(row.hire_date) > timedelta(days=3)]
        return rows_to_add, old_rows
    else:
        return rows_to_add

#Makes sure that hr and it are working with the same data, uses personal email (pmail) as primary key.
def compare_hr_it_emails(api_url, headers, valid_hr_rows, valid_it_rows):
    # Condition 1: Check if an email is in valid_it_rows but not in valid_hr_rows  
    it_rows_not_in_hr = [it_row for it_row in valid_it_rows if it_row.pmail not in {hr_row.pmail for hr_row in valid_hr_rows}]
    for it_row in it_rows_not_in_hr:
        delete_row(api_url, headers, it_row.row_id)

    # Condition 2: Check if an email is in valid_hr_rows but not in valid_it_rows
    hr_not_in_it_emails = [hr_row for hr_row in valid_hr_rows if hr_row.pmail not in {it_row.pmail for it_row in valid_it_rows}]
    for hr_row in hr_not_in_it_emails:
        create_row(api_url, headers, hr_row.to_json())

#Main function that runs everything
def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))#Added to make sure environment works correctly

    start_time = time.time()
    api_key = check_api_key()
    configure_logging()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    hr_url = "https://api.smartsheet.com/2.0/sheets/*hr_sheet_id*"
    hr_data = pull_data(hr_url, headers)

    it_url = "https://api.smartsheet.com/2.0/sheets/*it_sheet_id*"
    it_data = pull_data(it_url, headers)

    if hr_data and it_data:
        print("Working... please wait")
        #Main
        valid_hr_rows = clean_data_based_on_dates_hr(hr_data)
        valid_it_rows, delete_these_rows = clean_data_based_on_dates_it(it_data, True)

        archive_old_it_rows(it_url, headers, delete_these_rows) 
        replace_mismatched_dates(it_url, headers, valid_hr_rows, valid_it_rows)

        valid_it_rows= clean_data_based_on_dates_it(pull_data(it_url, headers))
        compare_hr_it_emails(it_url, headers, valid_hr_rows, valid_it_rows)
        sort_rows(it_url, headers)
        update_colors_for_it_rows(it_url, headers, valid_it_rows)


    else: #Failure to retrieve data
        print("Could not retrieve data! Please check that the website is up and that the API key hasn't expired.")
        sys.exit(0)
    print("Sheet refresh finished!")
    print("--- Program took %s seconds to execute ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()

