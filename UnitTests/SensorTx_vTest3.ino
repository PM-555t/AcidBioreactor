//includes
#include <Wire.h>    //i2c library
#include "MS5837.h"  //Blue Robotics pressure sensor

//10/9/24 - float switch test
//Madison M7790
int floatSW = 2;
int floatState = 0;

//global vars
int PARval = 0;          //for PAR sensor
float PARvolts = 0.0;    //for PAR sensor
int LICORval = 0;        //for LICOR CO2 sensor
float LICORvolts = 0.0;  //for LICOR CO2 sensor
MS5837 pressSens;        //Blue Robotics pressure sensor
#define pHaddress 99     //default i2c ID number for EZO pH Circuit.
#define DOaddress 100    //default i2c ID number for EZO DO Circuit.
String frameStart = "ZZ,";
String frame = "";
String temp = "";

//below is for Atlas probes
char computerdata[20];            //we make a 20 byte character array to hold incoming data from a pc/mac/other.
byte received_from_computer = 0;  //we need to know how many characters have been received.
byte pHcode = 0;                  //used to hold the I2C response code.
byte DOcode = 0;                  //used to hold the I2C response code.
char ph_data[32];                 //we make a 32 byte character array to hold incoming data from the pH circuit.
char DO_data[32];                 //we make a 32 byte character array to hold incoming data from the DO circuit.
byte in_char = 0;                 //used as a 1 byte buffer to store inbound bytes from the pH Circuit.
byte i = 0;                       //counter used for ph_data array.
int time_ = 815;                  //used to change the delay needed depending on the command sent to the EZO Class pH Circuit. 575 for DO.
float ph_forTest;
float ph_float;                   //float var used to hold the float value of the pH.
float DO_float;                   //float var used to hold the float value of the D.O.
float sat_float;                  //float var used to hold the float value of the percent saturation.
//specific to DO
char *DO;   //char pointer used in string parsing.
char *sat;  //char pointer used in string parsing.


void setup() {
  ph_forTest = 0.001;
  Serial.begin(115200);  //to send out to the Pi
  Wire.begin();          //start an i2c line (used for pressure sensor and the Atlas probes)

  // Initialize pressure sensor. Returns true if initialization was successful. We can't continue with the rest of the program unless we can initialize the sensor.
  while (!pressSens.init()) {
    Serial.println("Init failed!");
    Serial.println("Are SDA/SCL connected correctly?");
    Serial.println("Blue Robotics Bar30: White=SDA, Green=SCL");
    Serial.println("\n\n\n");
    delay(5000);
  }

  pressSens.setFluidDensity(1.204);  //kg/m3 for sea level air.

  //10/9/24
  pinMode(floatSW, INPUT_PULLUP);
}

void string_pars() {  //this function will break up the DO's CSV string into its 2 individual parts. DO|SAT|
                      //this is done using the C command “strtok”.

  DO = strtok(DO_data, ",");  //let's pars the string at each comma.
  sat = strtok(NULL, ",");    //let's pars the string at each comma.

  //Serial.print("DO:");                //we now print each value we parsed separately.
  //Serial.println(DO);                 //this is the D.O. value.

  //Serial.print("SAT:");               //we now print each value we parsed separately.
  //Serial.println(sat);                //this is the percent saturation.
  //Serial.println();                   //this just makes the output easier to read by adding an extra blank line

  //convert them into floating point number.
  DO_float = atof(DO);
  sat_float = atof(sat);
}

void loop() {
  //10/9/24
  floatState = digitalRead(floatSW);

  PARval = analogRead(A0);             //Retrieve...
  PARvolts = PARval * (5.0 / 1023.0);  //...and convert PAR sensor reading
  //insert conversion to umol once known

  LICORval = analogRead(A1);               //Retrieve...
  LICORvolts = LICORval * (5.0 / 1023.0);  //...and convert LICOR sensor reading to volts
  //insert conversion to ppm CO2 once set in the LICOR

  pressSens.read();  //Retrieve all fields for BR pressure sensor (i.e. pressSens.pressure() in mbar, pressSens.temperature() in deg C, etc.)

  //pH sensor
  time_ = 650;                        //set lower since polling will be automatic
  Wire.beginTransmission(pHaddress);  //circuit ID
  Wire.write("R");                    //single reading
  Wire.endTransmission();             //and close

  delay(time_);  //wait the correct amount of time for the circuit to complete its instruction.

  Wire.requestFrom(pHaddress, 32, 1);  //call the circuit and request 32 bytes (this may be more than we need)
  pHcode = Wire.read();                //the first byte is the response code, we read this separately.

  switch (pHcode) {  //switch case based on what the response code is.
    case 1:          //decimal 1.
      //Serial.println("Success");    		//means the command was successful.
      break;  //exits the switch case.

    case 2:  //decimal 2.
      //Serial.println("Failed");     		//means the command has failed.
      break;  //exits the switch case.

    case 254:  //decimal 254.
      //Serial.println("Pending");    		//means the command has not yet been finished calculating.
      break;  //exits the switch case.

    case 255:  //decimal 255.
      //Serial.println("No Data");    		//means there is no further data to send.
      break;  //exits the switch case.
  }

  while (Wire.available()) {  //are there bytes to receive.
    in_char = Wire.read();    //receive a byte.
    ph_data[i] = in_char;     //load this byte into our array.
    i += 1;                   //incur the counter for the array element.
    if (in_char == 0) {       //if we see that we have been sent a null command.
      i = 0;                  //reset the counter i to 0.
      break;                  //exit the while loop.
    }
  }

  ph_float = atof(ph_data);  //convert pH data array to a float
  if (pHcode != 1) {
    ph_float = -1.0;
  }

  //DO sensor
  time_ = 500;                        //set lower since polling will be automatic
  Wire.beginTransmission(DOaddress);  //circuit ID
  Wire.write("R");                    //single reading
  Wire.endTransmission();             //and close

  delay(time_);  //wait the correct amount of time for the circuit to complete its instruction.

  Wire.requestFrom(DOaddress, 32, 1);  //call the circuit and request 32 bytes (this may be more than we need)
  DOcode = Wire.read();                //the first byte is the response code, we read this separately.

  switch (DOcode) {  //switch case based on what the response code is.
    case 1:          //decimal 1.
      //Serial.println("Success");    		//means the command was successful.
      break;  //exits the switch case.

    case 2:  //decimal 2.
      //Serial.println("Failed");     		//means the command has failed.
      break;  //exits the switch case.

    case 254:  //decimal 254.
      //Serial.println("Pending");    		//means the command has not yet been finished calculating.
      break;  //exits the switch case.

    case 255:  //decimal 255.
      //Serial.println("No Data");    		//means there is no further data to send.
      break;  //exits the switch case.
  }

  while (Wire.available()) {  //are there bytes to receive.
    in_char = Wire.read();    //receive a byte.
    ph_data[i] = in_char;     //load this byte into our array.
    i += 1;                   //incur the counter for the array element.
    if (in_char == 0) {       //if we see that we have been sent a null command.
      i = 0;                  //reset the counter i to 0.
      break;                  //exit the while loop.
    }
  }

  if (DOcode != 1) {
    DO_float = -1.0;
  }

  if (computerdata[0] == 'r') string_pars();  //break up the DO's comma separated string into its individual parts.

  //concatenate all the sensor readings --> CO2 volts, pH reading, PAR reading, DO reading, pressure, press sensor temp, DO code, pH code
  frame = frameStart + LICORvolts + "," + String(ph_forTest) + "," + PARvolts + "," + String(DO_float) + "," + String(pressSens.pressure() * 0.0145)
          + "," + String((pressSens.temperature() * 1.8) + 32.0) + "," + String(DOcode) + "," + String(pHcode) + "," + String(floatState) + "\r\n";
  Serial.print(frame);  //send information to the Pi

  ph_forTest = ph_forTest + 0.001;

  //10/9/24
  //String testMessage = "Float switch:" + String(floatState) + "\r\n";
  //Serial.print(testMessage);

  delay(5000);
}
