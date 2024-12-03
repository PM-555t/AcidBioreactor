# AcidBioreactor

Operates a sequence of 3 pumps to appropriately mix acid effluent and seawater (and remove excess volume) as needed to keep CO2 and pH within desired ranges in a microalgal culture.

# File designations:
+ SensorTx_v* = Arduino C++ code to send and receive all sensor messages. Enumerates i2c communication for pH and DO reader boards, takes analog or digital measurements of the rest of the sensors. Combines all inputs into an ASCII string frame and transmits via serial (USB) directly to Pi.
+ PyLog_v* = Python script which runs on the Pi in a TMUX thread. Takes incoming ASCII frame, logs to a CSV. Rather than trying to manage the incoming stream and the state machine all in one place, this separation of scripts ensures the CSV is stored to memory in the event of process crashes.
+ BioReactor = Implements a state machine interface so that necessary flags, timers, current state, and state transition functions are global and/or asynchronous.
+ PyState_v* = Python script which runs on the Pi in a TMUX thread. Pulls the most recent data from the log file using a 'tail' call (which needs to be filtered for unchanged lines). Operates the state machine and contains the logic of each state, as well as the hardcoded "set" values chosen to gate state transitions.

# Dated notes:
- 10/9/2024 - SensorTx_v2.ino currently uploaded to Arduino. In PyState_v0.py, acidification state code is commented out to prevent pumps from running without any liquid. LICOR CO2 calibration has not been coded in anywhere; since PyState still creates a variable called "CO2 Volts", the volts-to-ppm conversion should probably be done there; this will also be simpler to manage during remote coding than making edits on the Arduino, which require manual connection. PyLog is hardcoded to /dev/ttyACM0 for now!!! Important to remember since the Pi has no requirement to keep the device name static (i.e. it could be ACM1 or ACM2 on connection loss). Also, pH and DO probes have not been calibrated and so are likely to provide erronous readings upon liquid contact.

# Running checklist:
- [x] Deal with PyLog possibly losing connection.
- [ ] Test Float switch
    - [x] PyState : Move float switch check to main loop
    - [x] PyState : Edit state code (and BioReactor object to allow it); if in [Acidify], excess until the switch turns off and then some extra. If in [Dilution_B], excess 1 L and go to [Incubate].
    - [ ] Check and test edited code
- [x] PyState : Fix log datetime formatting to put colon between date and hour.
- [ ] Physically test which pump isn't able to draw liquid.
- [x] Make this checklist!