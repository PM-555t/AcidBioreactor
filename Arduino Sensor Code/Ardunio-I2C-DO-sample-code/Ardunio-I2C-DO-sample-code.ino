//This code will work on an Arduino Uno and Mega
//This code was written to be easy to understand.
//Modify this code as you see fit.
//This code will output data to the Arduino serial monitor.
//Type commands into the Arduino serial monitor to control the EZO D.O. Circuit.
//This code was written in the Arduino 2.0 IDE
//This code was last tested 10/2022


#include <Wire.h>                //enable I2C.
#define address 100               //default I2C ID number for EZO DO Circuit.



char computerdata[32];           //we make a 32 byte character array to hold incoming data from a pc/mac/other.
byte received_from_computer = 0; //we need to know how many characters have been received.
byte serial_event = 0;           //a flag to signal when data has been received from the pc/mac/other.
byte code = 0;                   //used to hold the I2C response code.
char do_data[32];                //we make a 32 byte character array to hold incoming data from the D.O. circuit.
byte in_char = 0;                //used as a 1 byte buffer to store inbound bytes from the D.O. Circuit.
byte i = 0;                      //counter used for DO_data array.
int time_ = 575;                 //used to change the delay needed depending on the command sent to the EZO Class DO Circuit.

char *DO;                        //char pointer used in string parsing.
char *sat;                       //char pointer used in string parsing.

float DO_float;                  //float var used to hold the float value of the D.O.
float sat_float;                 //float var used to hold the float value of the percent saturation.


void setup()                     //hardware initialization.
{
  Serial.begin(9600);            //enable serial port.
  Wire.begin();                  //enable I2C port.
}


void serialEvent() {                                                              //this interrupt will trigger when the data coming from the serial monitor(pc/mac/other) is received.
  received_from_computer = Serial.readBytesUntil(13, computerdata, 32);          //we read the data sent from the serial monitor(pc/mac/other) until we see a <CR>. We also count how many characters have been received.
  computerdata[received_from_computer] = 0;                                       //stop the buffer from transmitting leftovers or garbage.
  serial_event = true;                                                            //set the serial event flag.
}


void loop() {                                                                     //the main loop.
 if (serial_event == true) {                                                      //if a command was sent to the EZO device.
    for (i = 0; i <= received_from_computer; i++) {                               //set all char to lower case, this is just so this exact sample code can recognize the "sleep" command.
      computerdata[i] = tolower(computerdata[i]);                                 //"Sleep" ≠ "sleep"
    }
    i=0;                                                                          //reset i, we will need it later 
    if (computerdata[0] == 'c' || computerdata[0] == 'r')time_ = 575;             //if a command has been sent to calibrate or take a reading we wait 575ms so that the circuit has time to take the reading.
    else time_ = 250;                                                             //if any other command has been sent we wait only 250ms.
 

    Wire.beginTransmission(address);                                        //call the circuit by its ID number.
    Wire.write(computerdata);                                               //transmit the command that was sent through the serial port.
    Wire.endTransmission();                                                 //end the I2C data transmission.


    if (strcmp(computerdata, "sleep") != 0) {                               //if the command that has been sent is NOT the sleep command, wait the correct amount of time and request data.
                                                                            //if it is the sleep command, we do nothing. Issuing a sleep command and then requesting data will wake the D.O. circuit.

      delay(time_);                                                         //wait the correct amount of time for the circuit to complete its instruction.

      Wire.requestFrom(address, 32, 1);                                     //call the circuit and request 32 bytes (this is more than we need)
      code = Wire.read();                                                   //the first byte is the response code, we read this separately.

      switch (code) {                           //switch case based on what the response code is.
        case 1:                                 //decimal 1.
          Serial.println("Success");            //means the command was successful.
          break;                                //exits the switch case.

        case 2:                                 //decimal 2.
          Serial.println("Failed");             //means the command has failed.
          break;                                //exits the switch case.

        case 254:                               //decimal 254.
          Serial.println("Pending");            //means the command has not yet been finished calculating.
          break;                                //exits the switch case.

        case 255:                               //decimal 255.
          Serial.println("No Data");            //means there is no further data to send.
          break;                                //exits the switch case.
      }

      while (Wire.available()) {                 //are there bytes to receive.
        in_char = Wire.read();                   //receive a byte.
        do_data[i] = in_char;                    //load this byte into our array.
        i += 1;                                  //incur the counter for the array element.
        if (in_char == 0) {                      //if we see that we have been sent a null command.
          i = 0;                                 //reset the counter i to 0.
          break;                                 //exit the while loop.
        }
      }

      Serial.println(do_data);                  //print the data.
      Serial.println();                         //this just makes the output easier to read by adding an extra blank line 
    }
    serial_event = false;                       //reset the serial event flag.

    //if (computerdata[0] == 'r') string_pars(); //uncomment this function if you would like to break up the comma separated string into its individual parts.
  }

}
void string_pars() {                  //this function will break up the CSV string into its 2 individual parts. DO|SAT|
                                      //this is done using the C command “strtok”.

  DO = strtok(do_data, ",");          //let's pars the string at each comma.
  sat = strtok(NULL, ",");            //let's pars the string at each comma.
 
  Serial.print("DO:");                //we now print each value we parsed separately.
  Serial.println(DO);                 //this is the D.O. value.

  Serial.print("SAT:");               //we now print each value we parsed separately.
  Serial.println(sat);                //this is the percent saturation.
  Serial.println();                   //this just makes the output easier to read by adding an extra blank line 
    
  //uncomment this section if you want to take the values and convert them into floating point number.
/*  
    DO_float=atof(DO);
    sat_float=atof(sat);
*/  
}
