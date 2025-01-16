import csv
import sys
import tkinter
import tkinter.filedialog as fd
import os
from pathlib import Path
import glob
import tkinter.messagebox

tkinter.Tk().withdraw()
foldername = fd.askdirectory(title='CSV folder selection')
if foldername:
    print('Folder selected')
else:
    tkinter.messagebox.showinfo(title='CSV parser',message='Please select a folder.')
    sys.exit(1)

def get_CSV_array(folderName):
    joined_files = os.path.join(folderName, "*.csv") 
    joined_list = glob.glob(joined_files) 

    final_file = []
    for fi in joined_list:
        csvName = os.path.basename(fi)
        year = csvName[0:4]
        month = csvName[4:6]
        day = csvName[6:8]
        date = (month+"/"+day+"/"+year)

        lasthour = -1
        with open(fi, "r") as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                hour = row[0].split(":")[0]
                if lasthour != -1:
                    if (hour<lasthour):
                        day = str(int(day) + 1)
                        date = (month+"/"+day+"/"+year) #this will break if day is last of the month, but fix that later
                lasthour = hour
                row.remove('bZZ')
                row.insert(0,date)
                final_file.append(row)

    return final_file

#acquire that single list of lists
try:
    allCSV = get_CSV_array(foldername)
except ValueError as e:
    tkinter.messagebox.showinfo(title='CSV parser',message='A Combined.csv may already be present, please delete and try again. If not, the CSVs may not be formatted correctly.')
    sys.exit(1)
except:
    tkinter.messagebox.showinfo(title='CSV parser',message='Something went wrong with the CSVs.')
    sys.exit(1)

#insert headers
allCSV.insert(0,['Date','Time','CO2 volts','pH','PAR volts','DO (mg per L)','Pressure (psia)','Temperature (deg F)','DO code','pH code','float SW'])

#write out final file
with open((str(Path(foldername)) + "\\Combined.csv"), 'w', newline='') as out:
    for line in allCSV:
        out.write(','.join(line))
        out.write('\n')

tkinter.messagebox.showinfo(title='CSV parser',message='Run is complete, see folder for a Combined.csv.')