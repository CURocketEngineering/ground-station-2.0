'''
PortSource.py

Scans for available data sources (Windows, Linux/Mac)
Needs file lookup for both windows/linux CSV and radio port

Tasks:
1) Determine operating system to find the right path formats
2) Returns an array of possible paths for the system

In simplier terms, we need a way to find every possible radio/csv pathway available to the operating system
'''

path_to_csv = "src/ground_station/backend/recordings"
options = []

import os
import platform
import serial.tools.list_ports

# Returns 1 if on windows, 2 for a linux-based, and raises an expection if not one of those two
def validOS():
    os_name = platform.system()

    if os_name == "Windows":
        return 1
    if os_name == "Darwin" == "Linux":
        return 2
    
    raise Exception("Invalid Operating System from PortSource")

''''
validPorts()

returns a list of valid ports for serial/radio communication

'''
def validPorts():
    os_num = validOS()

    if os_num == 1: # Windows
        ports = serial.tools.list_ports.comports()

        for p in ports:
            if p.startswith("COM"):
                options.append(p)

    elif os_num == 2: # linux
        source_start = "/dev"
        for f in os.listdir(source_start):        
            if f.startswith("tty."):
                options.append(os.path.join(source_start, f))

    if not options:
        raise Exception("No valid radio ports found")

    return options

'''
validCSVFiles()

returns a list of valid .csv files within the recordings folder of
'''
def validCSVFiles():
    for f in os.listdir(path_to_csv):
        if not f.endswith(".csv"):
            options.append(os.path.join(path_to_csv, f))

    if not options:
        raise Exception("No valid CSV files found in recordings directory (checks locally in ground_station)")

    return options

'''
Returns the path to a data source based on the desired path type

Source types: "Radio", "Serial", "CSV"
'''
def dataSourcePath(sourceType):
    if sourceType == "Serial":
        return validPorts()
    if sourceType == "CSV":
        return validCSVFiles()

    raise Exception("Invalid source selection for dataSourePath")