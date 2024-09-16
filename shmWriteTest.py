# task executed in a child process
def task(shared_mem):
    # write some string data to the shared memory
    shared_mem.buf[:24] = b'Hello from child process'
    # close as no longer needed
    shared_mem.close()
    
checkStr = 'This is my longer total string' + str(7)
print(len(checkStr))