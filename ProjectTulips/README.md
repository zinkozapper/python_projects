# Project Tulips

A script to generate weekly reports of events in Snipe-IT

## Getting Started

Select the project from the folder and either download raw or copy raw into a file.

### Prerequisites

The things you need before installing the software.

* Python 3.11.3+
* Various Python Packages
* Snipe-IT API Key

### Installation

A step by step guide that will tell you how to get the development environment up and running.

```
$ pip install requests argparse datetime
$ python3 .\ProjectTulips.py -h
```
Edit the file on line 90 and 101. Change *API_URL* to the api url of your Snipe-IT Server.
## Arguments

List of arguments to provide in the commandline for the tool.

```
options:
  -h, --help            show this help message and exit
  -a APIKEY, --apikey APIKEY
                        Add API Key
  -o OUTPUT, --output OUTPUT
                        Output file name
  -ci, --checkin        Checkin report
  -co, --checkout       Checkout report
  -d, --hardware        Avaliable device report
  -t TIMEPERIOD, --timeperiod TIMEPERIOD
                        time period for reports in days (default = 7)
```

