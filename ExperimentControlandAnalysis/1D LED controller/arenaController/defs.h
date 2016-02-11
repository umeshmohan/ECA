/*
STCP - SPI SS - teensy 3.1 SS pin10/anypin
SHCP - SPI SCK - teensy 3.1 SCK 13/14
DS - SPI MOSI - teensy 3.1 DOUT 11/7
OE - PWM analogwrite - teensy 3.1 pins 3,4,5,6,9,10,20,21,22,23,25,32

nextpin - Input from DAQ to switch display to next pattern in sequence
*/

#define STCPpin 10
#define SHCPpin 13
#define DSpin 11
#define OEpin 3
#define nextpin 23

#define SERtimeout 10

// Byte codes
#define GET_COMMAND 0xcc

#define FORWARD 0
#define BACKWARD 1
#define CLOCKWISE 2
#define COUNTERCLOCKWISE 3
#define SPOTCLOCKWISE 4
#define SPOTCOUNTERCLOCKWISE 5

int ts;
#define WaitTillSerialInputAvailableOrTimeout \
ts = millis();\
while (Serial.available() == 0) {\
  if (ts - millis() > SERtimeout) {\
    break;\
  }\
}

