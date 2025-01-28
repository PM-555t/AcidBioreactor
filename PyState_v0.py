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
import _thread

'''Send start command, then after x seconds...'''
def runPump(addr, seconds, loggername):
    #bus = smbus.SMBus(channel) --> moved this down to the initializition block, since calls are made at startup using it
    relayAddr = addr
    bus.write_i2c_block_data(boardAddr,relayAddr,[0xFF]) #turn on
    t = threading.Timer(seconds,shutOffPump,args=[boardAddr,relayAddr,bus,loggername,]) #turn off
    t.daemon = True #so if main thread closes, this timer also closes; won't turn pump off though!
    t.start()
    logger = logging.getLogger(loggername)
    logger.debug('Pump run:'+str(addr)+":"+str(seconds))
    return t

'''...send stop command'''
def shutOffPump(board,relay,bus,loggername):
    bus.write_i2c_block_data(board,relay,[0x00])
    logger = logging.getLogger(loggername)
    logger.debug('Pump disabled:'+str(relay))

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
    switchTimerFlag(reactorObj,majorOrMinor,False)
    t2 = threading.Timer(secs,switchTimerFlag,args=[reactorObj,majorOrMinor,True,])
    t2.daemon = True #so if main thread closes, this timer also closes; won't switch Timer flag in that case
    t2.start()
    return t2

'''Retrieve the config values'''
def ConfigRetrieve():
    '''Looks for a file named BioreactorConfig.ini in the /.Config folder.
    This will need to be formatted per the ConfigEditor.exe output
    and contain only floats.'''
    config_object = ConfigParser()

    #check that config is in the correct folder and properly named
    try:
        configLocation = (Path(__file__).parent / "Config\\BioreactorConfig.ini")
        config_object.read(configLocation)
    except:
        print('Cannot find or load config file')
        logger.error('Cannot find or load config file')
        _thread.interrupt_main()

    #check sections separately from existence
    try:
        cfgSets = config_object["SETPOINTS"]
        cfgVols = config_object["VOLUMES"]
        cfgTimes = config_object["TIMES"]
        cfgCals = config_object["CALIBRATIONS"]
    except:
        print('Config file is missing a section.')
        logger.error('Config file is missing a section.')
        _thread.interrupt_main()

    #Then make sure all values are good
    count = 0
    sectionList = ["SETPOINTS","VOLUMES","TIMES","CALIBRATIONS"]
    for section in sectionList:
        currentGroup = config_object.items(section)
        i = 0
        while (i < len(currentGroup)):
            try:
                float(currentGroup[i][1])
            except ValueError:
                count = count + 1
                print(currentGroup[i])
            i = i + 1
    if (count>0):
        print('Config file has improperly formatted values.')
        logger.error('Config file has improperly formatted values.')
        _thread.interrupt_main()

    return [cfgSets,cfgVols,cfgTimes,cfgCals]

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

'''Initiating logging'''
import logging
import queue
from logging.handlers import QueueListener
from logging.handlers import RotatingFileHandler

log_queue = queue.Queue()
rot_queue_handler = RotatingFileHandler('StateMachineLog.log',maxBytes=100000,backupCount=10,encoding='utf-8') #this is non-blocking
queue_listener = QueueListener(log_queue,rot_queue_handler) #apparently in its own thread
queue_listener.start()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.addHandler(rot_queue_handler) #and the handler is attached to the logger

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(funcName)s:%(message)s', datefmt='%m/%d/%Y:%I:%M:%S:%p')
rot_queue_handler.setFormatter(formatter)
logger.debug('PyState initiated')

'''Start acquiring config file values'''
from configparser import ConfigParser
[sets,vols,times,cals] = ConfigRetrieve()

'''Block of variables and calls for peristaltic pump i2c control.'''
channel = 1 #confirm with hardware change
bus = smbus.SMBus(channel)
boardAddr = 0x10 #can later add code to detect; confirm these with hardware changes
addrSWPump = 0x02
addrAcidPump = 0x03
addrExcessPump = 0x04
primeTimeSWPump = times["primetimeswpump"] #time to prime the pumps at startup.
primeTimeAcidPump = times["primetimeacidpump"]
primeTimeExcessPump = times["primetimeexcesspump"]
pumpCal = cals["pumpcal"] #sec/mL, averaged across the three pumps
#apparently the code can hang if the pumps are issued start commands when already running, so make sure they're off
shutOffPump(boardAddr,addrSWPump,bus,__name__)
shutOffPump(boardAddr,addrAcidPump,bus,__name__)
shutOffPump(boardAddr,addrExcessPump,bus,__name__)
time.sleep(1.0)

#briefly prime the pumps on script start, if the user wants to
toPrime = input('Do you want to prime the pumps? Type [y/n] and press enter.\n')
if toPrime == 'y':
    print('Pumps primed.')
    logger.info('Pumps primed.')
    runPump(addrSWPump,primeTimeSWPump,__name__)
    time.sleep(1.0)
    runPump(addrAcidPump,primeTimeAcidPump,__name__)
    time.sleep(1.0)
    runPump(addrExcessPump,primeTimeExcessPump,__name__)
    time.sleep(6.0) #allow priming to complete before we get into state code
else:
    print('Pumps not primed.')
    logger.info('Pumps not primed.')

'''Start of main code'''
maxFileSize = 100000
#later, change the below code to sleep and check again, in case PyState starts before PyLog when Pi comes online
try:
    logName = findNewLog('*.csv')
    print('Active log: ' + logName)
    logger.info('Active log:'+logName)
except:
    print('File search failed')
    sys.exit()
f, p = startTail(logName)
print(str(f) + ',' + str(p))

#set up table for reading in log values
recentVals = pd.DataFrame(index=[1,2,3,4,5,6,7,8,9,10],columns=['Time','frame key','CO2','pH','PAR','DO',
                                                     'Pressure','Temperature','DO_code','pH_code','FloatSW'])
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
CO2ppm = float(0)
CO2cal = cals["co2cal"] #LICOR set with 0-5 V DAC, for 0-2000 ppm range, or 400 ppm/V. Arduino ADC is 10-bit, apparently, so overall resolution is 0.5 ppm.
pHval = float(0)
PARval = float(0)
PAR_cal = cals["parcal"] #(umol / (m^2*s)) / volt; range could be 266.7 to 1875 based on online numbers
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
pHset = sets["ph_set"]
CO2_max = 0 #just an empty value for now
CO2_set = sets["co2_set"] #in ppm, post converstion from voltage
tempCO2 = CO2_set #just a changeable placeholder value
dPHdT_set = sets["dphdt_set"] #pH units / hour; can change this later
incubatePhDelta = sets["incubatephdelta"]
dilutionVol = vols["dilutionvol"]
acidLimit = 40 #the total allowable added acid volume in State 40 (Acidification)
overflow = int(0) #0 for no, 1 for float SW in acidify, 2 for float SW in dilution
floatReleaseAttempts = int(0)

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
            logger.info('Active log:'+logName)
        #the below line (and function) is redundant now, right?
        isNew, logName = logOverSwap(logName) #each cycle, check if PyLog iterated the log file for size reasons        
        if isNew: #if it did...
            killTail(f) #...kill the old tail process...
            f, p = startTail(logName) #...and start a new one.
            print('Active log: ' + logName)
            logger.info('Active log:'+logName)
        
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
                recentVals.loc[dfIndex] = test #+ [dPHdT]
                recentVals.loc[dfIndex]['CO2'] = float(recentVals.loc[dfIndex]['CO2']) * CO2cal
                dfIndex = dfIndex + 1
                valChange = True
            else:
                pass
        else: #and then iterate down 1 row each sampling period
            sameLine = (recentVals.loc[10]['Time'] == test[0])
            if not sameLine:
                recentVals = recentVals.loc[:].shift(periods=-1,axis=0) #dont use fill_values because zeros affect mean
                recentVals.loc[10] = test #+ [dPHdT]
                recentVals.loc[10]['CO2'] = float(recentVals.loc[10]['CO2']) * CO2cal
                valChange = True
            else:
                pass
        
        '''If we actually have a new reading, then capture our averaged readings'''
        if valChange: 
            print(test)
            CO2ppm = recentVals['CO2'].astype(float).mean() #as of 1/8, is no longer labeled as CO2volts
            pHval = recentVals['pH'].astype(float).mean()
            PARval = recentVals['PAR'].astype(float).mean()
            DOval = recentVals['DO'].astype(float).mean()
            pressure = recentVals['Pressure'].astype(float).mean()
            temperature = recentVals['Temperature'].astype(float).mean()
            DOcode = int(test[8])
            pHcode = int(test[9])
            floatSW = int(test[10])
            
            #and insert our averaged readings into the long form table, if it's been long enough
            if ((time.monotonic() - lastLongTime) > 60):

                '''20241220 - code block inserted to calculate dPHdT as a moving average of
                the short table, as opposed to an average of "instant" dPHdT values'''
                if longIndex < 2:
                    longdPHdT = 0.0
                else:
                    dPH = pHval - longVals.loc[longIndex-1]['pH'] #(current average of last 60 seconds) - (last average of previous 60 seconds)
                    if dPH < 0.001:
                        dPH = 0
                    if dfIndex < 11:
                        if dfIndex == 1:
                            dT = 1000000000
                        else:
                            dT = (strSecDiff(recentVals.loc[1]['Time'],recentVals.loc[dfIndex-1]['Time'])/3600)
                    else:
                        dT = (strSecDiff(recentVals.loc[1]['Time'],recentVals.loc[10]['Time'])/3600)
                    longdPHdT = dPH / dT #pH units per hour
                    logger.debug("dPH:"+str(dPH)+":dT:"+str(dT)+":dPHdT:"+str(longdPHdT))
                    #print("Current dPH: "+str(dPH)+", dT: "+str(dT)+", dPHdT: "+str(longdPHdT))
                '''End 20241220 insert'''

                lastLongTime = time.monotonic()
                
                #CO2 volts is actually ppm now
                curArray = [lastLongTime,CO2ppm,pHval,PARval,DOval,pressure,temperature,DOcode,pHcode,floatSW,longdPHdT]
                #delimArrayString = (str(lastLongTime)+':'+str(CO2ppm)+':'+str(pHval)+':'+str(PARval)+':'+
                #                    str(DOval)+':'+str(pressure)+':'+str(temperature)+':'+str(DOcode)+':'+
                #                    str(pHcode)+':'+str(floatSW)+':'+str(longdPHdT))
                delimArrayString = (f'{myReactor._state.stateNumber:.0f}:{lastLongTime:.3f}:{CO2ppm:.1f}:{pHval:.3f}:{(PARval*PAR_cal):.1f}:'
                                    f'{DOval:.3f}:{pressure:.3f}:{temperature:.1f}:{DOcode:.0f}:{pHcode:.0f}:{floatSW:.0f}:{longdPHdT:.3f}')
                
                if longIndex < 61: #fill down initially
                    if not longVals.loc[longIndex][0] == lastLongTime:
                        longVals.loc[longIndex] = curArray
                        longIndex = longIndex + 1
                else: #and then iterate down 1 row each sampling period
                    if not longVals.loc[60][0] == lastLongTime:
                        longVals = longVals.loc[:].shift(periods=-1,axis=0)
                        longVals.loc[60] = curArray
                print("60 sec interval recorded") # just temp line for debugging
                logger.info('60s interval values:'+str(delimArrayString))
            
        '''Apparently, the seawater cycling should happen on a regular schedule'''
        '''To avoid pausing this script, another script and timer should
        be initiated to run the pumps for a certain amount of time'''
        #put in scheduler code here
        
        #Update the config values, in case the user has changed them
        [sets,vols,times,cals] = ConfigRetrieve()

        '''The state machine logic'''
        state = myReactor._state.stateNumber
        match state:
            case 40:
                if floatSW == 1:
                    if state != lastState:
                        logger.info('State change:'+str(state))
                        print("Acidification")
                        lastState = state
                        #Make sure timer completion flags are currently set to "finished"
                        switchTimerFlag(myReactor,True,True) #major timer
                        switchTimerFlag(myReactor,False,True) #minor timer
                        justPumped = False #reset flag for having run acid pump
                        myReactor._pumpOrMsr = False # reset flag for sub-state of pumping or measuring (to measuring)
                        #Update config values, but only when transitioning. Don't update every cycle.
                        pHset = sets["ph_set"]
                        acidLimit = vols["acidlimit"]
                    
                    #Below block commented out for testing purposes, 10-4-24
                    #in acidification, we add 1 mL of acid at a time, up to 15
                    #after adding each mL, we wait 1 minute
                    #then check if we've triggered our pH limit or we have too much volume
                    if (acidVolAdded <= acidLimit) and (pHval > pHset):
                        if justPumped == False: #first time running pump
                            runPump(addrAcidPump,pumpCal*1,__name__) #run pump for first time, for 1 mL
                            justPumped = True
                            myReactor._pumpOrMsr = True #set state to pumping, not measuring
                            pumpWaitTimer(myReactor,False,180.0) #set minor timer to 3 minutes
                            acidVolAdded = acidVolAdded + 1 #add to acidVolAdded
                        elif myReactor.curMinorTimer(): #just pumped AND timer finished; true means the timer has finished
                            runPump(addrAcidPump,pumpCal*1,__name__)
                            pumpWaitTimer(myReactor,False,180.0) 
                            acidVolAdded = acidVolAdded + 1 
                        else: #just pumped, but timer is not finished
                            pass
                    else:
                        myReactor._pumpOrMsr = False #measuring, not pumping
                        myReactor.nextState(50) #change to "Watch CO2"
                        acidVolAdded = 0

                    if overflow != 0:            
                        overflow = 0
                        logger.warning("Overflow state set to --> "+str(overflow))
                    
                    #myReactor.curPumpAction(): #just a leftover line to remember the function name
                else:
                    shutOffPump(boardAddr,addrAcidPump,bus,__name__) #turn off pump early
                    switchTimerFlag(myReactor,False,True) #turn off minor timer flag
                    overflow = 1
                    logger.warning("Overflow state set to --> "+str(overflow))
                    #Note- the below only runs if the float switch was active during the last read (~5-7 seconds ago)
                    #So if the float switch goes high again while waiting for the pump timer to finish, it goes back to acidify
                    if myReactor.curMinorTimer(): #make sure pump isn't running
                        myReactor._pumpOrMsr = False
                        myReactor.nextState(71) #switch to dilution
                        acidVolAdded = 0
                
                    
            case 50:
                if state != lastState:
                    logger.info('State change:'+str(state))
                    print("Watch CO2")
                    lastState = state
                    #Make sure timer completion flags are currently set to "finished"
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    justPumped = False #reset flag for having run acid pump
                    myReactor._pumpOrMsr = False # reset flag for sub-state of pumping or measuring (to measuring)
                    pumpWaitTimer(myReactor,True,3600)#start major timer for 1 hr
                    #Update config values, but only when transitioning. Don't update every cycle.
                    CO2_set = sets["co2_set"]
                    if longIndex > 1: #don't trust table or reading at first row
                        #Index should always be -1; 60 will be filled if index is 61, any other index should be chosen as previous
                        CO2_max = longVals.loc[longIndex - 1]['CO2']# * CO2cal; doesn't need to be converted, was already done in recentVals!
                    else:
                        CO2_max = CO2_set #basically just assuming CO2 = setpoint
                    
                #every loop, update current max CO2 reading
                tempCO2 = CO2_set
                if longIndex > 1: #don't trust table or reading at first row
                    #Index should always be -1; 60 will be filled if index is 61, any other index should be chosen as previous
                    tempCO2 = longVals.loc[longIndex-1]['CO2']# * CO2cal; doesn't need to be converted, was already done in recentVals!
                if tempCO2 > CO2_max:
                    CO2_max = tempCO2
                    
                #when timer is up, make decision --> low CO2 goes to S71, high CO2 goes to S60
                if myReactor.curMajorTimer(): #if the hour timer has finished...
                    logger.info('CO2_max = '+str(CO2_max))
                    if CO2_max < CO2_set:
                        myReactor.nextState(71) #move to dilution, too much algae is consuming too much CO2
                    else:
                        myReactor.nextState(60) #move to incubation, we need algae to consume more
                    
            case 60:
                if state != lastState:
                    logger.info('State change:'+str(state))
                    print("Incubate")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    #set major timer to 1 hr
                    pumpWaitTimer(myReactor,True,3600)
                    #Update config values, but only when transitioning. Don't update every cycle.
                    CO2_set = sets["co2_set"]
                    dPHdT_set = sets["dphdt_set"]
                    pHset = sets["ph_set"]
                    incubatePhDelta = sets["incubatephdelta"]
                
                #at the 1 hr mark, check the last 30 minutes of dPHdT and raw pH data
                if myReactor.curMajorTimer():
                    absMaxPhRate = abs(longVals.loc[30:60]['d(pH)/dt'].astype(float).max())
                    currpH = longVals.loc[58:60]['pH'].astype(float).mean() #average the last 3 minutes
                    
                    logger.info('Incubate; pH change rate: '+str(absMaxPhRate)+', avg pH: '+str(currpH))
                    CO2_check = longVals.loc[longIndex - 1]['CO2']
                    if (CO2_check < CO2_set):    
                        if (absMaxPhRate < dPHdT_set) and ((currpH - pHset) < incubatePhDelta): #to make basic again
                            myReactor.nextState(71)
                        elif (absMaxPhRate < dPHdT_set) and ((currpH - pHset) > incubatePhDelta): #to bring pH back down
                            myReactor.nextState(40)
                        #In the below case, CO2 is low enough but pH change rate is still too fast
                        else:
                            logger.info('Incubate exit conditions not met, timer reset to 10 minutes')
                            pumpWaitTimer(myReactor,True,600)                   
                    else: #if rate > set, reset the major timer to 10 minutes to check again
                        logger.info('Incubate exit conditions not met, timer reset to 10 minutes')
                        pumpWaitTimer(myReactor,True,600)
                    #This is where the code can get stuck but it's probably best that nothing is running if the pH probe is throwing wacky values
                
            case 71:
                if state != lastState:
                    #Update config values, but only when transitioning. Don't update every cycle.
                    dilutionVol = vols["dilutionvol"]
                    actualDilVol = dilutionVol
                    if overflow == 1:
                        actualDilVol = 100 #will excess 100 mL if we hit the limit switch during acidification
                    elif overflow == 2:
                        actualDilVol = 1000 #will excess 1 L if we hit the limit switch during dilution
                    floatReleaseAttempts = 0
                    logger.info('State change:'+str(state))
                    print("Dilute part a")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    runPump(addrExcessPump,pumpCal*actualDilVol,__name__) #run pump for X L
                    justPumped = True
                    myReactor._pumpOrMsr = True #set state to pumping, not measuring
                    pumpWaitTimer(myReactor,False,(pumpCal*actualDilVol)+60.0) #set minor timer to pump time + delay
                
                if myReactor.curMinorTimer(): #When pump is done...
                    if floatSW == 1 and overflow == 0: #...if we got here from Watch CO2...
                        justPumped = False
                        myReactor._pumpOrMsr = False
                        myReactor.nextState(72) #...move on to seawater addition.
                    elif floatSW == 1 and overflow == 1: #...if we got here from acidification and overflow but float SW back down...
                        overflow = 0 #...reset...
                        logger.warning("Overflow state set to --> "+str(overflow))
                        justPumped = False
                        myReactor._pumpOrMsr = False
                        myReactor.nextState(40) #...and go back to acidification.
                    elif floatSW == 1 and overflow == 2: #...if we got here from Dilution B (seawater) and overflow but float SW back down...
                        overflow = 0 #...reset...
                        logger.warning("Overflow state set to --> "+str(overflow))
                        justPumped = False
                        myReactor._pumpOrMsr = False
                        myReactor.nextState(60) #...and go to incubation.
                    elif floatSW < 1: #...if we haven't excessed enough...
                        if floatReleaseAttempts > 2:
                            logger.error('Exiting. Float switch is stuck, or liquid not leaving chamber.')
                            _thread.interrupt_main() #calls keyboard interrupt to exit for safety reasons
                        runPump(addrExcessPump,pumpCal*actualDilVol,__name__) #run pump for X L
                        justPumped = True
                        myReactor._pumpOrMsr = True
                        pumpWaitTimer(myReactor,False,(pumpCal*actualDilVol)) #set minor timer to pump time + delay
                        floatReleaseAttempts = floatReleaseAttempts + 1
                        print("Attempted to relieve float switch "+str(floatReleaseAttempts)+" times.")
                    
            case 72:
                if state != lastState:
                    #Update config values, but only when transitioning. Don't update every cycle.
                    dilutionVol = vols["dilutionvol"] #be aware of the risks of this changing between states 71 and 72!
                    logger.info('State change:'+str(state))
                    print("Dilute part b")
                    lastState = state
                    switchTimerFlag(myReactor,True,True) #major timer
                    switchTimerFlag(myReactor,False,True) #minor timer
                    runPump(addrSWPump,pumpCal*dilutionVol,__name__) #run pump for 5 L
                    justPumped = True
                    myReactor._pumpOrMsr = True #set state to pumping, not measuring
                    pumpWaitTimer(myReactor,False,(pumpCal*dilutionVol)+60.0) #set minor timer to pump time + delay
                
                if myReactor.curMinorTimer() or (floatSW < 1): #when pump is done or float switch active...
                    if floatSW < 1:
                        shutOffPump(boardAddr,addrSWPump,bus,__name__) #turn off pump early
                        switchTimerFlag(myReactor,False,True) #turn off minor timer flag
                        overflow = 2
                        logger.warning("Overflow state set to --> "+str(overflow))
                        myReactor.nextState(71) #go back to dilute part A (excess)
                    else:
                        myReactor.nextState(60) #...incubate new mixture a little
                        myReactor._pumpOrMsr = False #set state to measuring
                    
            case _:
                logger.error('Undefined bioreactor state.')
                print("Undefined bioreactor state")
                #if we get here, just close out
                bus = smbus.SMBus(channel)
                shutOffPump(boardAddr,addrSWPump,bus,__name__)
                shutOffPump(boardAddr,addrAcidPump,bus,__name__)
                shutOffPump(boardAddr,addrExcessPump,bus,__name__)
                killTail(f)
                sys.exit()
        
    except KeyboardInterrupt:
        #make sure to kill the tail command, if the command is exited manually
        killTail(f)
        #and kill pumps
        shutOffPump(boardAddr,addrSWPump,bus,__name__)
        shutOffPump(boardAddr,addrAcidPump,bus,__name__)
        shutOffPump(boardAddr,addrExcessPump,bus,__name__)
        #Make sure timers are complete
        TimerCnt = 0
        while (len(threading.enumerate()) > 1):
            for thread in threading.enumerate():
                if 'Timer' in str(thread):
                    TimerCnt = TimerCnt + 1
            print("Timers still running:",TimerCnt,"; Time:",time.monotonic())
            if TimerCnt == 0:
                break
            else:
                TimerCnt = 0
                time.sleep(1.0)
        time.sleep(1.0)
        logger.warning('PyState closed by KeyboardInterrupt')
        sys.exit()
        '''Not sure what to do if the script process crashes. This system may not
        run long enough for that to matter, though, as we don't expect a loop which
        depletes the process table by rapidly iterating process initiation and leaving
        it hanging.'''