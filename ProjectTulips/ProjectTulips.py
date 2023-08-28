import requests
import json
import csv
import sys
import argparse
from datetime import datetime, timedelta
import time

def argument_checker():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-a", "--apikey", type = str, required = True, help = "Add API Key")
    argParser.add_argument("-o", "--output", type = str, help = "Output file name")
    argParser.add_argument("-ci", "--checkin", action = 'store_true', help = "Checkin report")
    argParser.add_argument("-co", "--checkout", action = 'store_true', help = "Checkout report")
    argParser.add_argument("-d", "--hardware", action = 'store_true', help = "Avaliable device report")
    argParser.add_argument("-t", "--timeperiod", type = int, default = 7, help = "time period for reports in days (default = 7)")
    args = argParser.parse_args()
    return args

#Ask the api
def ping_api(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        data = response.json()  # Assuming the API returns JSON data
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

#Save an item and its properties
def save_row(file, writer, paged_data, k, report):
    row = []
    if (report.lower() == 'd' or report.lower() == 'h'):
        row.append(paged_data["rows"][k]["id"])
        row.append(paged_data["rows"][k]["name"])
        row.append(paged_data["rows"][k]["asset_tag"])
        row.append(paged_data["rows"][k]["serial"])
        if (paged_data["rows"][k]["model"]["name"] and paged_data["rows"][k]["model_number"]):
            row.append(paged_data["rows"][k]["model"]["name"] + paged_data["rows"][k]["model_number"])
        row.append(paged_data["rows"][k]["status_label"]["status_meta"])
        
    elif (report.lower() == 'ci' or report.lower() == 'co'):
        id = paged_data["rows"][k]["item"]["id"]
        if (id > 722):
            if(len(str(id))==3):
                row.append('\'00'+str(id))
            if(len(str(id))==4):
                row.append('\'0'+str(id))
        else:
            row.append('\'' + str(id-2))
        row.append(paged_data["rows"][k]["item"]["name"])
        row.append(paged_data["rows"][k]["action_type"])
        row.append(paged_data["rows"][k]["action_date"]["datetime"])
    else:
        print("Invalid report argument")
        return
    writer.writerow(row)

def date_calculations(data, i):
    json_dt = datetime.strptime(data["rows"][i]["action_date"]["datetime"], '%Y-%m-%d %H:%M:%S')
    # Get the current datetime
    current_dt = datetime.now()
    # Calculate the time difference
    time_difference = current_dt - json_dt
    return time_difference

def csv_file_check(csv_filename):
    if not csv_filename:
        csv_filename = "output.csv"
    if not csv_filename.endswith(".csv"):
        csv_filename += ".csv"
    return csv_filename

def report_determiner(args):
    otherTriggered = False
    if (args.checkin or args.checkout):
        if args.checkin:
            if otherTriggered:
                print("Multiple reports detected! Please select reports one at a time.")
                sys.exit()
            otherTriggered = True

        if args.checkout:
            if otherTriggered:
                print("Multiple reports detected! Please select reports one at a time.")
                sys.exit()
            otherTriggered = True

        api_url = "*API_URL*/reports/activity"
        labels = ["id", "name", "action", "datetime"]
        offset = 0
        limit = 50

    if args.hardware:
        if otherTriggered:
            print("Multiple reports detected! Please select reports one at a time.")
            sys.exit()
        otherTriggered = True

        api_url = "*API_URL*/hardware"
        labels = ["id", "name", "asset_tag", "serial", "model", "status"]
        offset = 0
        limit = 500
        
    if (args.hardware is False and args.checkin is False and args.checkout is False):
        print("Please select a report using the arguments (see -h)")
        sys.exit()
    return offset, limit, labels, api_url

def check_data_in_out(file, writer, data, args, max_save_size):
    for i in range(max_save_size):
            if (data["rows"][i]["action_type"] == "checkin from"):
                if (args.checkin):
                    save_row(file,writer,data,i, 'ci')
            if (data["rows"][i]["action_type"] == "checkout"):
                if (args.checkout):
                    save_row(file,writer,data,i, 'co')

def main():
    start_time = time.time()
    #Args init
    args = argument_checker()
    api_key = args.apikey
    csv_filename = csv_file_check(args.output)
    offset, sizeIncrease, labels, api_url = report_determiner(args)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    data = ping_api(api_url, headers)

    #CSV init
    file = open(csv_filename,"w",newline='')
    writer = csv.writer(file)
    
    if data:
        #Main loop
        print("Saving data...")
        writer.writerow(labels)
        total_results = data["total"]
        second_condition_trigger = False

    else: #Failure to retrieve data
        print("Could not retrieve data! Please check that the website is up and that the API key hasn't expired.")
        sys.exit(1)
     
    # Iterate until the request size is reduced to 1 or the condition is met
    if args.checkout or args.checkin:
        while sizeIncrease > 0:
            # Create a list of data with the current request size
            data = ping_api((f"{api_url}?offset={offset}&limit={sizeIncrease}"), headers=headers) # Replace 'get_next_unit' with your data retrieval logic

            if data:
                last_unit_dt = date_calculations(data,-1)
                if last_unit_dt < timedelta(days=args.timeperiod) and not second_condition_trigger :
                    offset = offset + sizeIncrease
                    check_data_in_out(file, writer, data, args, sizeIncrease)
                if date_calculations(data,sizeIncrease-1) >= timedelta(days=args.timeperiod):
                    second_condition_trigger = True
                    current_unit_dt = date_calculations(data,sizeIncrease-1)
                    sizeIncrease -=1
                    if (date_calculations(data,sizeIncrease-2) < timedelta(days=args.timeperiod)):
                        check_data_in_out(file, writer, data, args, sizeIncrease-1)
                        break 
    #check for hardware       
    elif data and args.hardware:
        total = data["total"]
        while offset <= total:
            data = ping_api((f"{api_url}?offset={offset}&limit={sizeIncrease}"), headers=headers)
            if data:
                for i in range(len(data["rows"])):
                    if (data["rows"][i]["status_label"]["status_meta"] != "deployed" and data["rows"][i]["status_label"]["status_meta"] != "archived"):       
                        save_row(file,writer,data,i, 'd')
                offset += sizeIncrease
            
    file.close()
    print(f"Data has been saved to '{csv_filename}'")
    print("--- Program took %s seconds to execute ---" % (time.time() - start_time))
          
if __name__ == "__main__":
    main()

