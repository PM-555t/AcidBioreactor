import time
import datetime
import serial
import pandas as pd
import csv
import sys

ser = serial.Serial(port='/dev/ttyACM0',baudrate=115200)

logName = datetime.datetime.today().strftime('%Y%m%d_%H%M') + '.csv'

#variables
writeStr = ""
lineRead = []

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
        b = open(logName,"a") #have to open and close to expose the last line
        writer = csv.writer(b)
        writer.writerow(test)
        b.close() #have to open and close to expose the last line
        print(test[0])
    except KeyboardInterrupt:
        b.close()
        print("File closed")
        sys.exit()