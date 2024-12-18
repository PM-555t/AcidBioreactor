import time
import datetime
import serial
import pandas as pd
import csv
import sys
import os
from pathlib import Path

try:
    ser = serial.Serial(port='/dev/ttyACM0',baudrate=115200)
except Exception as e:
    print("Unable to open serial port, with error: "+str(e))
    sys.exit()

logName = datetime.datetime.today().strftime('%Y%m%d_%H%M') + '.csv'

#variables
writeStr = ""
lineRead = []
serialAttempts = 0

#since the readline() only occurs when the Arduino passes one (every 6 seconds), this loop is triggered by that send
while True:
    try:
        x = ser.readline() #get line
        now = datetime.datetime.today().strftime('%H:%M:%S') #get current time
        
        writeStr = str(now) + "," + str(x) #add in timestamp to line
        writeStr = writeStr.replace("\\r\\n","") #remove newline chars
        writeStr = writeStr.replace("'","") #remove string-within-a-string
        lineRead = str(writeStr).split(",") #break the fields up
        test = lineRead[0:] #grab all fields
        
        #log the read before screwing around with it too much
        # Was a simple write before but it isn't setting proper newlines; moved to csvwriter and put parsing code in a different script
        #have to open and close to expose the last line
        myfile = Path(logName)
        if myfile.is_file():
            if (os.path.getsize(logName) > 100000) :
                logName = datetime.datetime.today().strftime('%Y%m%d_%H%M') + '.csv'
        b = open(logName,"a")
        writer = csv.writer(b)
        writer.writerow(test)
        b.close() #have to open and close to expose the last line
        print(test[0])
    except KeyboardInterrupt:
        b.close()
        print("File closed")
        ser.close()
        print("Serial port closed")
        sys.exit()
    except serial.SerialException:
        print("Serial error. Trying to reinitialize.")
        while serialAttempts < 3:
            try:
                ser.close()
                print("Port closed")
                time.sleep(1.0)
                ser = serial.Serial(port='/dev/ttyACM0',baudrate=115200)
                print("Port reinitialized")
                serialAttempts = 0 #for next time USB lost
                break #2024-12-12: I think this is the right level, but it needs to be tested
            except:
                serialAttempts = serialAttempts + 1
                print("Unable to reinitialize port on attempt: "+str(serialAttempts))
                time.sleep(3.0)

        if not (serialAttempts < 3):
            print("Unable to reinitialize serial port, closing PyLog.")
            sys.exit()
