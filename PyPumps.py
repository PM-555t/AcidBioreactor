import time
import smbus

def runPump(addr, seconds):
    statusBit = 0
    
    channel = 1 #need to confirm when running this way
    bus = smbus.SMBus(channel)
    
    boardAddr = 0x10 #can later add code to detect
    relayAddr = addr
    
    runStart = time.monotonic()
    bus.write_i2c_block_data(boardAddr,relayAddr,0xFF) #turn on
    time.sleep(seconds - ((time.monotonic() - runStart) %seconds)) #sleep for x seconds
    bus.write_i2c_block_data(boardAddr,relayAddr,0xFF) #turn off
    
    return statusBit