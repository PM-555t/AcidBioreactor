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
import threading
import smbus
import BioReactor

'''Send start command, then after x seconds...'''
def runPump(addr, seconds):
    bus = smbus.SMBus(channel)
    relayAddr = addr
    bus.write_i2c_block_data(boardAddr,relayAddr,[0xFF]) #turn on
    t = threading.Timer(seconds,shutOffPump,args=[boardAddr,relayAddr,bus,]) #turn off
    t.start()
    return t

'''...send stop command'''
def shutOffPump(board,relay,bus):
    bus.write_i2c_block_data(board,relay,[0x00])

'''Initiates a process which calls the typical CLI Tail function'''
def startTail(theLogName):
    #to avoid trying to open and close the log file from two scripts, just call 'tail' and pipe it
    fnow = subprocess.Popen(['tail','-F',theLogName],\
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pnow = select.poll()
    pnow.register(fnow.stdout)
    print('Reader started')
    return fnow, pnow

'''Closes the tail when necessary to preserve memory and entries
in the process table'''
def killTail(fToKill):
    process = psutil.Process(fToKill.pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    print("Reader process killed")

'''Find all CSV files, then determine newest, then open newest'''
def findNewLog(typeStr):
    list_of_files = glob.glob(typeStr)
    nameStr = max(list_of_files, key=os.path.getctime)
    return nameStr

'''Find and return new log name if log file got too big'''
def logOverSwap(theLogName):
    myfile = Path(theLogName)
    wasDiff = False
    if myfile.is_file():
        if (os.path.getsize(theLogName) > maxFileSize):
            theLogName = findNewLog('*.csv')
            wasDiff = True
            print('Active log: ' + theLogName)
    return wasDiff, theLogName

'''Switching timer flags on and off'''
def switchTimerFlag(BRobject,majorMinor,startStop): #majorMinor = True is the major timer; startStop = False is start
    if majorMinor:
        BRobject._majorTimerDone = startStop
    else:
        BRobject._minorTimerDone = startStop

'''The actual timer which swaps the flags'''
def pumpWaitTimer(reactorObj,majorOrMinor,secs): #majorOrMinor = True is the major timer
    switchTimer(reactorObj,majorOrMinor,False)
    t2 = threading.Timer(secs,switchTimerFlag,args=[reactorObj,majorOrMinor,True,])

'''Calculate the time difference, in seconds, between two of the time strings in the log'''
def strSecDiff(startTime,endTime):
    hrDiff = 0
    minDiff = 0
    secDiff = 0

    secTest = str(startTime).split(":")
    secTest2 = str(endTime).split(":")

    startHr = int(secTest[0])
    startMin = int(secTest[1])
    startSec = int(secTest[2])
    endHr = int(secTest2[0])
    endMin = int(secTest2[1])
    endSec = int(secTest2[2])

    if endHr < startHr:
        hrDiff = (24 - startHr) + endHr
    else:
        hrDiff = endHr - startHr

    if endMin < startMin:
        if hrDiff > 0:
            hrDiff = hrDiff - 1
        minDiff = (60 - startMin) + endMin
    else:
        minDiff = endMin - startMin

    if endSec < startSec:
        if minDiff > 0:
            minDiff = minDiff - 1
        secDiff = (60 - startSec) + endSec
    else:
        secDiff = endSec - startSec

    secCount = secDiff + (minDiff*60) + (hrDiff*(60*60))
    return secCount

'''Block of variables and calls for peristaltic pump i2c control.
I need to doublecheck the below block's values before 1st run.'''
channel = 1 #need to confirm when running this way
boardAddr = 0x10 #can later add code to detect
addrSWPump = 0x02
addrAcidPump = 0x03
addrExcessPump = 0x04
primeTimeSWPump = 5.0 #time to prime the pumps at startup. Set now, change later.
primeTimeAcidPump = 5.0
primeTimeExcessPump = 5.0
pumpCal = 0.581395 #sec/mL, averaged across the three pumps
#briefly prime the pumps on script start
runPump(addrSWPump,primeTimeSWPump)
time.sleep(1.0)
runPump(addrAcidPump,primeTimeAcidPump)
time.sleep(1.0)
runPump(addrExcessPump,primeTimeExcessPump)

'''Start of main code'''
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
recentVals = pd.DataFrame(index=[1,2,3,4,5,6,7,8,9,10],columns=['Time','frame key','CO2','pH','PAR','DO',
                                                     'Pressure','Temperature','DO_code','pH_code','FloatSW','d(pH)/dt'])
longVals = pd.DataFrame(index=pd.RangeIndex(start=1, stop=61, step=1),columns=['Time','CO2','pH','PAR','DO',
                                                     'Pressure','Temperature','DO_code','pH_code','Last FloatSW','d(pH)/dt'])
recentVals.fillna(0)
longVals.fillna(0)
dfIndex = int(1)
longIndex = int(1)
curLine = "" #variable for last line
lastLongTime = time.monotonic()

#variables that will be parsed; instantiate just for memory purposes
CO2volts = float(0)
CO2cal = 400.0 #LICOR set with 0-5 V DAC, for 0-2000 ppm range, or 400 ppm/V. Arduino ADC is 10-bit, apparently, so overall resolution is 0.5 ppm.
pHval = float(0)
PARval = float(0)
DOval = float(0)
pressure = float(0)
temperature = float(0)
DOcode = int(0)
pHcode = int(0)
floatSW = int(1)
dPHdT = float(0) #pH units per hour
longdPHdT = float(0)
#lazyPhTime = time.monotonic()

#variables for state machine
state = int(0)
lastState = int(0)
valChange = False
pumpOrMsr = False #a sub-state
justPumped = False
acidVolAdded = int(0)
pHset = 6.5 #can change this later
CO2_max = 0 #just an empty value for now
CO2_set = 400 #in ppm, post converstion from voltage
tempCO2 = CO2_set #just a changeable placeholder value
dPHdT_set = 0.2 #pH units / hour; can change this later
dilutionVol = 5000

myReactor = BioReactor.Reactor(BioReactor.Acidification())
print("State number:",myReactor._state.stateNumber)

#loop initation time, for timers
#do I still need the below, given how I've implemented the timers?
startTime = time.monotonic()
lastAcidTime = time.monotonic()
lastSWTime = time.monotonic()
pumpOn = False

#To Add: what happens if PyLog restarts while PyState is running?
#Currently, PyState can handle the file being reset because it's too large.
#But what if there is just a new file because PyLog restarted.
#Should probably check for a new file on every loop. Logging is slow anyways.
while True:
    try:
        '''First things first, we need to make sure we're always watching the most current log each cycle.'''
        logCheck = findNewLog('*.csv') #check to see if a newer csv was generated because PyLog cycled
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
        
        '''Then we grab the last line from the most current log file'''
        #call the tail command, then wait 1 second and try again
        if p.poll(1):
            curLine = f.stdout.readline()
        time.sleep(1)
        #since this doesn't check for updates, we need to check if the line is new or old
        
        '''Extract out the array for each new line'''
        curLine = str(curLine).replace("\\r\\n","") #remove newline chars
        curLine = str(curLine).replace("'","") #remove string-within-a-string
        curLine = str(curLine).replace("b","") #remove byte designations
        test = str(curLine).split(",") #break the fields up
        
        '''To avoid sensor issues triggering system behavior, we want to average the
        last 10 readings (which ends up being about 60-70 seconds delay), so we need to construct
        a running table of values. Because of the way the tail function works (i.e. grabs
        the last line whether it's new or not), we have to check each line before inserting.'''
        valChange = False
        #fill the table of the last 10 values
        if dfIndex < 11:
            sameLine = True
            if dfIndex == 1:
                sameLine = (recentVals.loc[dfIndex]['Time'] == test[0])
            else:
                sameLine = (recentVals.loc[dfIndex-1]['Time'] == test[0])
            if not sameLine: #if the line isn't the same as the one being inserted
                if dfIndex == 1:
                    dPHdT = 0.0
                else:
                    dPH = (float(test[3])-float(recentVals.loc[dfIndex-1]['pH']))
                    dT = (strSecDiff(recentVals.loc[dfIndex-1]['Time'],test[0])/3600)
                    dPHdT =  dPH / dT
                    if (abs(dPHdT) > 0.02) and (abs(dPH) < 0.02): #catch little fluctuations
                        dPHdT = 0.0
                recentVals.loc[dfIndex] = test + [dPHdT]
                recentVals.loc[dfIndex]['CO2'] = float(recentVals.loc[dfIndex]['CO2']) * CO2cal
                dfIndex = dfIndex + 1
                valChange = True
            else:
                pass
        else: #and then iterate down 1 row each sampling period
            sameLine = (recentVals.loc[10]['Time'] == test[0])
            if not sameLine:
                dPH = (float(test[3])-float(recentVals.loc[10]['pH']))
                dT = (strSecDiff(recentVals.loc[10]['Time'],test[0])/3600)
                dPHdT = dPH / dT #so this is a single point FBD; replace with more intelligent derivative in the future
                
                if (abs(dPHdT) > 0.02) and (abs(dPH) < 0.02): #catch little fluctuations
                        dPHdT = 0.0
                
                recentVals = recentVals.loc[:].shift(periods=-1,axis=0) #dont use fill_values because zeros affect mean
                recentVals.loc[10] = test + [dPHdT]
                recentVals.loc[10]['CO2'] = float(recentVals.loc[10]['CO2']) * CO2cal
                valChange = True
            else:
                pass
        
        '''If we actually have a new reading, then capture our averaged readings'''
        if valChange: 
            print(test + [dPHdT])
            CO2volts = recentVals['CO2'].astype(float).mean() #as of 10/15, is actually CO2 ppm
            pHval = recentVals['pH'].astype(float).mean()
            PARval = recentVals['PAR'].astype(float).mean()
            DOval = recentVals['DO'].astype(float).mean()
            pressure = recentVals['Pressure'].astype(float).mean()
            temperature = recentVals['Temperature'].astype(float).mean()
            DOcode = int(test[8])
            pHcode = int(test[9])
            floatSW = int(test[10])
            longdPHdT = recentVals['d(pH)/dt'].astype(float).mean()
            #and insert our averaged readings into the long form table, if it's been long enough
            if ((time.monotonic() - lastLongTime) > 60):
                lastLongTime = time.monotonic()
                
                curArray = [lastLongTime,CO2volts,pHval,PARval,DOval,pressure,temperature,DOcode,pHcode,floatSW,longdPHdT]                
                if longIndex < 61: #fill down initially
                    if not longVals.loc[longIndex][0] == lastLongTime:
                        longVals.loc[longIndex] = curArray
                        longIndex = longIndex + 1
                else: #and then iterate down 1 row each sampling period
                    if not longVals.loc[60][0] == lastLongTime:
                        longVals = longVals.loc[:].shift(periods=-1,axis=0)
                        longVals.loc[60] = curArray
                print("60 sec interval recorded") # just temp line for debugging
                print(longVals) # just temp line for debugging
                print("Avg pH rate:",longdPHdT) #just temp line for debugging
            
        '''Apparently, the seawater cycling should happen on a regular schedule'''
        '''To avoid pausing this script, another script and timer should
        be initiated to run the pumps for a certain amount of time'''
        #put in scheduler code here
        
        '''The state machine logic'''
        state = myReactor._state.stateNumber
        match state:
            case 40:
                if state != lastState:
                    print("Acidification")
                    lastState = state
                    #Make sure timer completion flags are currently set to "finished"
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    justPumped = False #reset flag for having run acid pump
                    myReactor._pumpOrMsr = False # reset flag for sub-state of pumping or measuring (to measuring)
                
                #Below block commented out for testing purposes, 10-4-24
                #in acidification, we add 1 mL of acid at a time, up to 15
                #after adding each mL, we wait 1 minute
                #then check if we've triggered our pH limit or we have too much volume
                if (acidVolAdded <= 15) and (pHval > pHset):
                    if justPumped = False: #first time running pump
                        runPump(addrAcidPump,pumpCal*1) #run pump for first time, for 1 mL
                        justPumped = True
                        myReactor._pumpOrMsr = True #set state to pumping, not measuring
                        pumpWaitTimer(myReactor,False,60.0) #set minor timer to 1 minute
                        acidVolAdded = acidVolAdded + 1 #add to acidVolAdded
                    elif myReactor.curMinorTimer(): #just pumped AND timer finished; true means the timer has finished
                        runPump(addrAcidPump,pumpCal*1)
                        pumpWaitTimer(myReactor,False,60.0) 
                        acidVolAdded = acidVolAdded + 1 
                    else: #just pumped, but timer is not finished
                        pass
                else:
                    myReactor._pumpOrMsr = False #measuring, not pumping
                    myReactor.nextState(50) #change to "Watch CO2"
                               
                #myReactor.curPumpAction(): #just a leftover line to remember the function name
                
                    
            case 50:
                if state != lastState:
                    print("Watch CO2")
                    lastState = state
                    #Make sure timer completion flags are currently set to "finished"
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    justPumped = False #reset flag for having run acid pump
                    myReactor._pumpOrMsr = False # reset flag for sub-state of pumping or measuring (to measuring)
                    pumpWaitTimer(myReactor,True,300)#start major timer for 5 min
                    if longIndex > 1: #don't trust table or reading at first row
                        CO2_max = longVals.loc[longIndex]['CO2'].astype(float) * CO2cal #convert from volts to ppm
                    else:
                        CO2_max = CO2_set #basically just assuming CO2 = setpoint
                    
                #every loop, update current max CO2 reading
                tempCO2 = CO2_set
                if longIndex > 1: #don't trust table or reading at first row
                    tempCO2 = longVals.loc[longIndex]['CO2'].astype(float) * CO2cal #convert from volts to ppm
                if tempCO2 > CO2_max:
                    CO2_max = tempCO2
                    
                #when timer is up, make decision --> low CO2 goes to S71, high CO2 goes to S60
                if myReactor.curMajorTimer(): #if the hour timer has finished...
                    if CO2_max < CO2_set:
                        myReactor.nextState(71) #move to dilution, too much algae is consuming too much CO2
                    else:
                        myReactor.nextState(60) #move to incubation, we need algae to consume more
                    
            case 60:
                if state != lastState:
                    print("Incubate")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    #set major timer to 1 hr
                    pumpWaitTimer(myReactor,True,3600)
                
                #at the 1 hr mark, check the last 30 minutes of dPHdT and raw pH data
                if myReactor.curMajorTimer():
                    absMaxPhRate = abs(longVals.loc[30:60]['d(pH)/dt'].astype(float).max())
                    currpH = longVals.loc[58:60]['pH'].astype(float).mean() #average the last 3 minutes
                    
                    if (absMaxPhRate < dPHdT_set) and ((currpH - pHset) < 0.5): #to make basic again
                        myReactor.nextState(71)
                    elif (absMaxPhRate < dPHdT_set) and ((currpH - pHset) > 0.5): #to bring pH back down
                        myReactor.nextState(40)                   
                    else: #if rate > set, reset the major timer to 10 minutes to check again
                        pumpWaitTimer(myReactor,True,600)
                    #This is where the code can get stuck but it's probably best that nothing is running if the pH probe is throwing wacky values
                
            case 71:
                if state != lastState:
                    print("Dilute part a")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    runPump(addrExcessPump,pumpCal*dilutionVol) #run pump for 5 L
                    justPumped = True
                    myReactor._pumpOrMsr = True #set state to pumping, not measuring
                    pumpWaitTimer(myReactor,False,(pumpCal*dilutionVol)+60.0) #set minor timer to pump time + delay
                
                if myReactor.curMinorTimer(): #when pump is done...
                    myReactor.nextState(72) #...move on to SW addition
                    
            case 72:
                if state != lastState:
                    print("Dilute part b")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    runPump(addrSWPump,pumpCal*dilutionVol) #run pump for 5 L
                    justPumped = True
                    myReactor._pumpOrMsr = True #set state to pumping, not measuring
                    pumpWaitTimer(myReactor,False,(pumpCal*dilutionVol)+60.0) #set minor timer to pump time + delay
                
                if myReactor.curMinorTimer() or (longVals.loc[60]['Last FloatSW'].astype(float) < 1): #when pump is done or float switch active...
                    myReactor.nextState(60) #...incubate new mixture a little
                    myReactor._pumpOrMsr = False #set state to measuring
                    
            case _:
                print("Undefined bioreactor state")
                #if we get here, just close out
                bus = smbus.SMBus(channel)
                shutOffPump(boardAddr,addrSWPump,bus)
                shutOffPump(boardAddr,addrAcidPump,bus)
                shutOffPump(boardAddr,addrExcessPump,bus)
                killTail(f)
                sys.exit()
        
    except KeyboardInterrupt:
        #make sure to kill the tail command, if the command is exited manually
        killTail(f)
        sys.exit()
        '''Not sure what to do if the script process crashes. This system may not
        run long enough for that to matter, though, as we don't expect a loop which
        depletes the process table by rapidly iterating process initiation and leaving
        it hanging.'''