import pandas as pd
import sys
import csv
import time
import subprocess
import select
import psutil
import glob
import os
from pathlib import Path

def startTail(theLogName):
    #to avoid trying to open and close the log file from two scripts, just call 'tail' and pipe it
    fnow = subprocess.Popen(['tail','-F',theLogName],\
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pnow = select.poll()
    pnow.register(fnow.stdout)
    print('Reader started')
    return fnow, pnow

def killTail(fToKill):
    process = psutil.Process(fToKill.pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    print("Reader process killed")

def findNewLog(typeStr):
    #find all CSV files, then determine newest, then open newest
    list_of_files = glob.glob(typeStr)
    nameStr = max(list_of_files, key=os.path.getctime)
    return nameStr

def logOverSwap(theLogName):
    myfile = Path(theLogName)
    wasDiff = False
    if myfile.is_file():
        if (os.path.getsize(theLogName) > maxFileSize):
            theLogName = findNewLog('*.csv')
            wasDiff = True
            print('Active log: ' + theLogName)
    return wasDiff, theLogName


#start of main code
maxFileSize = 100000
#later, change the below code to sleep and check again, in case PyState starts before PyLog when Pi comes online
try:
    logName = findNewLog('*.csv')
    print('Active log: ' + logName)
except:
    print('File search failed')
    sys.exit()
f, p = startTail(logName)
print(str(f) + ',' + str(p))

#set up table for reading in log values
recentVals = pd.DataFrame(index=[1,2,3,4,5],columns=['Time','frame key','CO2','pH','PAR','DO',
                                                     'Pressure','Temperature','DO_code','pH_code'])
recentVals.fillna(0)
dfIndex = int(1)
curLine = "" #variable for last line

#variables that will be parsed; instantiate just for memory purposes
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

#To Add: what happens if PyLog restarts while PyState is running?
#Currently, PyState can handle the file being reset because it's too large.
#But what if there is just a new file because PyLog restarted.
#Should probably check for a new file on every loop. Logging is slow anyways.
while True:
    try:
        logCheck = findNewLog('*.csv')#each cycle, check to see if a newer csv was generated because PyLog cycled
        if not logCheck == logName:
            logName = logCheck
            killTail(f) #...kill the old tail process...
            f, p = startTail(logName) #...and start a new one.
            print('Active log: ' + logName)
        #the below line (and function) is redundant now, right?
        isNew, logName = logOverSwap(logName) #each cycle, check if PyLog iterated the log file for size reasons        
        if isNew: #if it did...
            killTail(f) #...kill the old tail process...
            f, p = startTail(logName) #...and start a new one.
            print('Active log: ' + logName)
        
        #call the tail command, then wait 1 second and try again
        if p.poll(1):
            curLine = f.stdout.readline()
        time.sleep(1)
        #since this doesn't check for updates, we need to check if the line is new or old
        
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
        killTail(f)
        sys.exit()