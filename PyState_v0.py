import pandas as pd
import sys
import csv
import time
import subprocess
import select
import psutil
import glob
import os

#hardcoded for now, rewrite to be file search later
list_of_files = glob.glob('*.csv') # * means all if need specific format then *.csv
logName = max(list_of_files, key=os.path.getctime)
print("Active log: " + logName)
#logName = "20240909.csv"

#to avoid trying to open and close the log file from two scripts, just call 'tail' and pipe it
f = subprocess.Popen(['tail','-F',logName],\
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
p = select.poll()
p.register(f.stdout)
curLine = "" #variable for last line

#set up table for reading in log values
recentVals = pd.DataFrame(index=[1,2,3,4,5],columns=['Time','frame key','CO2','pH','PAR','DO',
                                                     'Pressure','Temperature','DO_code','pH_code'])
recentVals.fillna(0)
dfIndex = int(1)

# variables that will be parsed; instantiate just for memory purposes
CO2volts = float(0)
pHval = float(0)
PARval = float(0)
DOval = float(0)
pressure = float(0)
temperature = float(0)
DOcode = int(0)
pHcode = int(0)

#for state machine
state = int(0)
valChange = False

while True:
    try:
        #call the tail command, then wait 1 second and try again
        if p.poll(1):
            curLine = f.stdout.readline()
            #print(curLine)
        time.sleep(1)
        #given how this works, we need to check if the line is new or old
        
        #extract out the array for each new line
        curLine = str(curLine).replace("\\r\\n","") #remove newline chars
        curLine = str(curLine).replace("'","") #remove string-within-a-string
        curLine = str(curLine).replace("b","") #remove byte designations
        test = str(curLine).split(",") #break the fields up
        
        valChange = False
        #fill the table of the last 5 values
        if dfIndex < 6: #fill the first 5 rows
            if not recentVals.loc[dfIndex][0] == test[0]:
                recentVals.loc[dfIndex] = test
                dfIndex = dfIndex + 1
                valChange = True
        else: #and then iterate down 1 row each sampling period
            if not recentVals.loc[5][0] == test[0]:
                recentVals = recentVals.loc[:].shift(periods=-1,axis=0) #dont use fill_values because zeros affect mean
                recentVals.loc[5] = test
                valChange = True
        
        if valChange: #if we actually have a new reading, then capture our averaged readings
            print(test)
            CO2volts = recentVals['CO2'].astype(float).mean()
            pHval = recentVals['pH'].astype(float).mean()
            PARval = recentVals['PAR'].astype(float).mean()
            DOval = recentVals['DO'].astype(float).mean()
            pressure = recentVals['Pressure'].astype(float).mean()
            temperature = recentVals['Temperature'].astype(float).mean()
            DOcode = int(test[8])
            pHcode = int(test[9])
                
    except KeyboardInterrupt:
        #make sure to kill the tail command
        process = psutil.Process(f.pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
        print("Reader process killed")
        sys.exit()
