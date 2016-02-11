#include "defs.h"

#include <SPI.h>

volatile unsigned int currentOffset = 0,
                      patternType = 0,
                      patternSize = 10,
                      currentBrightness = 65520;

volatile bool arenaUpdated = false,
              brightnessUpdated = false;

byte pattern[40];

SPISettings settingsA(10000000, LSBFIRST, SPI_MODE0);

void setup() {
  analogWriteResolution(16);
  pinMode(OEpin, OUTPUT);
  pinMode(STCPpin, OUTPUT);
  pinMode(SHCPpin, OUTPUT);
  pinMode(DSpin, OUTPUT);
  digitalWrite(STCPpin, HIGH);
  SPI.begin();

  setPattern(pattern, 0xff, 0, 0);
  updateArena();
  Serial.begin(115200);
  while (!Serial){;}
  setPattern(pattern, -1, 0, 0);
  updateArena();
  
  pinMode(nextpin, INPUT_PULLUP);  
  attachInterrupt(nextpin, nextInSequence, FALLING);
  Serial.print("Ready\n\n");
}

void loop() {
  char t = 0x00;
  if (Serial.available() > 0) {
    t = Serial.read();
    if (t == 0xcc) {
      getCommand();
    }
  }
}

void nextInSequence() {
  cli();
  if (patternType == 0 || patternType == 2 || patternType == 4 || patternType == 5 ) {
    currentOffset = currentOffset + 1;
  }
  else if (patternType == 1 || patternType == 3) {
    currentOffset = currentOffset - 1;
  }
  setPattern(pattern, patternType, patternSize, currentOffset);
  updateArena();
  sei();
}

void getCommand() {
  unsigned char command;
  WaitTillSerialInputAvailableOrTimeout
  command = Serial.read();
  if (command == 0x01) {
    getBrightnessFromSerial();
  }
  else if (command == 0x02) {
    getPatternParametersFromSerial();
  }
}

void getBrightnessFromSerial() {
  union {
    char c[2];
    unsigned int b;
  } t;
  WaitTillSerialInputAvailableOrTimeout
  t.c[0] = Serial.read();
  WaitTillSerialInputAvailableOrTimeout
  t.c[1] = Serial.read();
  currentBrightness = t.b;
  analogWrite(OEpin, currentBrightness);
}

void getPatternParametersFromSerial() {
  union {
    char c[2];
    unsigned int b;
  } t;
  WaitTillSerialInputAvailableOrTimeout
  t.c[0] = Serial.read();
  WaitTillSerialInputAvailableOrTimeout
  t.c[1] = Serial.read();
  patternType = t.b;
  WaitTillSerialInputAvailableOrTimeout
  t.c[0] = Serial.read();
  WaitTillSerialInputAvailableOrTimeout
  t.c[1] = Serial.read();
  patternSize = t.b;
  cli();
  currentOffset = 0;
  setPattern(pattern, patternType, patternSize, currentOffset);
  updateArena();
  sei();
}

