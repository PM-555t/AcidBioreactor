import time
import serial

ser = serial.Serial(
    port='/dev/ttyACM0',baudrate=9600,parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,bytesize=serial.EIGHTBITS,timeout=1)

while True:
    x=ser.readline()
    b=open("20240828_3.txt","a")
    b.write(str(x))
    b.close()