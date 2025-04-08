import tkinter as tk
import tkinter.filedialog as fd
from configparser import ConfigParser

class App(tk.Frame):
    def __init__(self,master=None,**kw):
        #Create a blank dictionary
        self.answers = {}
        tk.Frame.__init__(self,master=master,**kw)

        self.entry_list = []

        ##### Setpoints
        tk.Label(self,text="pH setpoint").grid(row=0,column=0)
        self.ph_set = tk.Entry(self)
        self.ph_set.grid(row=0,column=1)
        self.entry_list.append(self.ph_set)

        tk.Label(self,text="CO2 setpoint (ppm)").grid(row=1,column=0)
        self.CO2_set = tk.Entry(self)
        self.CO2_set.grid(row=1,column=1)
        self.entry_list.append(self.CO2_set)

        tk.Label(self,text="d(pH)/dt setpoint (pH/hour)").grid(row=2,column=0)
        self.dphdt_set = tk.Entry(self)
        self.dphdt_set.grid(row=2,column=1)
        self.entry_list.append(self.dphdt_set)

        tk.Label(self,text="Incubate pH delta").grid(row=3,column=0)
        self.incubate_ph_delta = tk.Entry(self)
        self.incubate_ph_delta.grid(row=3,column=1)
        self.entry_list.append(self.incubate_ph_delta)

        ##### Volumes
        tk.Label(self,text="Dilution volume (mL)").grid(row=0,column=2)
        self.dilution_vol = tk.Entry(self)
        self.dilution_vol.grid(row=0,column=3)
        self.entry_list.append(self.dilution_vol)

        tk.Label(self,text="Acid addition limit (mL)").grid(row=1,column=2)
        self.acid_limit = tk.Entry(self)
        self.acid_limit.grid(row=1,column=3)
        self.entry_list.append(self.acid_limit)

        tk.Label(self,text="Acid overflow excess amt (mL)").grid(row=2,column=2)
        self.overflow1 = tk.Entry(self)
        self.overflow1.grid(row=2,column=3)
        self.entry_list.append(self.overflow1)

        tk.Label(self,text="Dilution overflow excess amt (mL)").grid(row=3,column=2)
        self.overflow2 = tk.Entry(self)
        self.overflow2.grid(row=3,column=3)
        self.entry_list.append(self.overflow2)

        ##### Times
        tk.Label(self,text="Priming time, SW pump (sec)").grid(row=0,column=4)
        self.primetime_SW_pump = tk.Entry(self)
        self.primetime_SW_pump.grid(row=0,column=5)
        self.entry_list.append(self.primetime_SW_pump)

        tk.Label(self,text="Priming time, acid pump (sec)").grid(row=1,column=4)
        self.primetime_acid_pump = tk.Entry(self)
        self.primetime_acid_pump.grid(row=1,column=5)
        self.entry_list.append(self.primetime_acid_pump)

        tk.Label(self,text="Priming time, excess pump (sec)").grid(row=2,column=4)
        self.primetime_excess_pump = tk.Entry(self)
        self.primetime_excess_pump.grid(row=2,column=5)
        self.entry_list.append(self.primetime_excess_pump)

        tk.Label(self,text="Wait time, CO2 watch (sec)").grid(row=3,column=4)
        self.watch_CO2_wait = tk.Entry(self)
        self.watch_CO2_wait.grid(row=3,column=5)
        self.entry_list.append(self.watch_CO2_wait)

        tk.Label(self,text="Wait time, Incubate (sec)").grid(row=4,column=4)
        self.incubate_wait = tk.Entry(self)
        self.incubate_wait.grid(row=4,column=5)
        self.entry_list.append(self.incubate_wait)

        tk.Label(self,text="Wait time, Incubate re-check (sec)").grid(row=5,column=4)
        self.incubate_rewait = tk.Entry(self)
        self.incubate_rewait.grid(row=5,column=5)
        self.entry_list.append(self.incubate_rewait)

        ##### Calibrations
        tk.Label(self,text="CO2, ppm/volt").grid(row=0,column=6)
        self.CO2_cal = tk.Entry(self)
        self.CO2_cal.grid(row=0,column=7)
        self.entry_list.append(self.CO2_cal)
        
        tk.Label(self,text="Acid pump speed, sec/mL").grid(row=1,column=6)
        self.acidpumpcal = tk.Entry(self)
        self.acidpumpcal.grid(row=1,column=7)
        self.entry_list.append(self.acidpumpcal)

        tk.Label(self,text="SW pump speed, sec/mL").grid(row=2,column=6)
        self.swpumpcal = tk.Entry(self)
        self.swpumpcal.grid(row=2,column=7)
        self.entry_list.append(self.swpumpcal)

        tk.Label(self,text="Excess pump speed, sec/mL").grid(row=3,column=6)
        self.excesspumpcal = tk.Entry(self)
        self.excesspumpcal.grid(row=3,column=7)
        self.entry_list.append(self.excesspumpcal)
        
        tk.Label(self,text="PAR cal, umol/volt").grid(row=4,column=6)
        self.parcal = tk.Entry(self)
        self.parcal.grid(row=4,column=7)
        self.entry_list.append(self.parcal)
        
        ##### Buttons
        tk.Button(self,text="Save config file",command = self.captureConfig).grid(row=7,column=1)
        tk.Button(self,text="Retrieve current config",command = self.retrieveConfig).grid(row=7,column=0)
        tk.Button(self,text="Exit",command = self.close_window).grid(row=7,column=2)

        self.file_opt = options = {}
        options['filetypes'] = [('config files', '.ini'), ('all files', '.*')]
        options['initialfile'] = 'Rename_Me.ini'
        options['parent'] = root

    def close_window(self):
        root.destroy()

    def retrieveConfig(self):
        #Read config.ini file
        config_object = ConfigParser()
        configLocation = fd.askopenfilename(title='Config file selection')
        if configLocation:
            for entry in self.entry_list:
                entry.delete(0,tk.END)

            config_object.read(configLocation)
            
            sets = config_object["SETPOINTS"]
            self.ph_set.insert(0,sets["ph_set"])
            self.CO2_set.insert(0,sets["co2_set"])
            self.dphdt_set.insert(0,sets["dphdt_set"])
            self.incubate_ph_delta.insert(0,sets["incubatephdelta"])

            vols = config_object["VOLUMES"]
            self.dilution_vol.insert(0,vols["dilutionvol"])
            self.acid_limit.insert(0,vols["acidlimit"])
            self.overflow1.insert(0,vols["overflow1"])
            self.overflow2.insert(0,vols["overflow2"])

            times = config_object["TIMES"]
            self.primetime_SW_pump.insert(0,times["primetimeswpump"])
            self.primetime_acid_pump.insert(0,times["primetimeacidpump"])
            self.primetime_excess_pump.insert(0,times["primetimeexcesspump"])
            self.watch_CO2_wait.insert(0,times["watchco2wait"])
            self.incubate_wait.insert(0,times["incubatewait"])
            self.incubate_rewait.insert(0,times["incubaterewait"])

            cals = config_object["CALIBRATIONS"]
            self.CO2_cal.insert(0,cals["co2cal"])
            self.acidpumpcal.insert(0,cals["acidpumpcal"])
            self.swpumpcal.insert(0,cals["swpumpcal"])
            self.excesspumpcal.insert(0,cals["excesspumpcal"])
            self.parcal.insert(0,cals["parcal"])

    def captureConfig(self):
        entryChecks = 0
        numberProbs = 0
        for entry in self.entry_list:
            if not entry.get():
                entryChecks = entryChecks + 1
            else:
                try:
                    float(entry.get())
                except ValueError:
                    numberProbs = numberProbs + 1
        if entryChecks > 0:        
            tk.messagebox.showwarning(title="Incomplete submission",message=f"There are {entryChecks:.0f} empty fields, please fix.")
            return
        if numberProbs > 0:
            tk.messagebox.showwarning(title="Incorrect submission",message=f"There are {numberProbs:.0f} fields with number issues, please fix.")
            return
        
        #Setpoints
        self.answers['ph_set'] = self.ph_set.get()
        self.answers['CO2_set'] = self.CO2_set.get()
        self.answers['dphdt_set'] = self.dphdt_set.get()
        self.answers['incubatephdelta'] = self.incubate_ph_delta.get()
        #Volumes
        self.answers['dilutionvol'] = self.dilution_vol.get()
        self.answers['acidlimit'] = self.acid_limit.get()
        self.answers['overflow1'] = self.overflow1.get()
        self.answers['overflow2'] = self.overflow2.get()
        #Times
        self.answers['primetimeswpump'] = self.primetime_SW_pump.get()
        self.answers['primetimeacidpump'] = self.primetime_acid_pump.get()
        self.answers['primetimeexcesspump'] = self.primetime_excess_pump.get()
        self.answers['watchco2wait'] = self.watch_CO2_wait.get()
        self.answers['incubatewait'] = self.incubate_wait.get()
        self.answers['incubaterewait'] = self.incubate_rewait.get()
        #Calibrations
        self.answers['co2cal'] = self.CO2_cal.get()
        self.answers['acidpumpcal'] = self.acidpumpcal.get()
        self.answers['swpumpcal'] = self.swpumpcal.get()
        self.answers['excesspumpcal'] = self.excesspumpcal.get()
        self.answers['parcal'] = self.parcal.get()

        config_out = ConfigParser()
        config_out["SETPOINTS"] = {
            "pH_set": self.answers['ph_set'], 
            "CO2_set": self.answers['CO2_set'], 
            "dPHdT_set": self.answers['dphdt_set'], 
            "incubatePHdelta": self.answers['incubatephdelta'] 
        }
        config_out["VOLUMES"] = {
            "dilutionVol": self.answers['dilutionvol'],
            "acidLimit": self.answers['acidlimit'],
            "overflow1": self.answers['overflow1'], 
            "overflow2": self.answers['overflow2']
        }
        config_out["TIMES"] = {
            "primeTimeSWPump": self.answers['primetimeswpump'],
            "primeTimeAcidPump": self.answers['primetimeacidpump'],
            "primeTimeExcessPump": self.answers['primetimeexcesspump'],
            "watchCO2wait": self.answers['watchco2wait'], 
            "incubateWait": self.answers['incubatewait'], 
            "incubateReWait": self.answers['incubaterewait']
        }
        config_out["CALIBRATIONS"] = {
            "CO2cal": self.answers['co2cal'], 
            "acidpumpCal": self.answers['acidpumpcal'],
            "swpumpCal": self.answers['swpumpcal'],
            "excesspumpCal": self.answers['excesspumpcal'],
            "PARcal": self.answers['parcal']
        }

        filename = fd.asksaveasfilename(**self.file_opt)
        if filename:
            print(filename)

            #Write the above sections to config.ini file
            with open(filename, 'w') as conf:
                config_out.write(conf)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Set configuration details for Acid Bioreactor")
    App(root).grid()
    root.mainloop()