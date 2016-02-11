void setPattern(byte *pattern, int patternType, int patternSize, int offset_) {
  memset(pattern,0,40);
  int i, j, k, l;
  if (patternType == 0 || patternType == 1) { //forward or backward 
    offset_ = offset_ % patternSize;
    for (i = 0; i < 160; i++) {
      j = i / 8;
      k = i % 8;
      if (((i + offset_) % patternSize) < patternSize/2) {
        bitSet(pattern[j], k);
        bitSet(pattern[39 - j], (7-k));
      }
    }
  }
  else if (patternType == 2 || patternType ==3) { //clockwise or counterclockwise
    offset_ = offset_ % patternSize;
    for (i = 0; i < 320; i++) {
      j = i / 8;
      k = i % 8;
      if (((i + offset_) % patternSize) < patternSize/2) {
        bitSet(pattern[j], k);
      }
    }
  }
  else if (patternType == 4 || patternType == 5) { //spot clockwise or spot counterclockwise
    offset_ = offset_ % 320;
    for (i = offset_; i < (offset_ + (patternSize / 2)); i++) {
      if (patternType == 4) {
        j = (319 - i) / 8;
        k = (319 - i) % 8;
      }
      else {
        j = i / 8;
        k = i % 8;
      }
      bitSet(pattern[j], k);
    }
  }
  else if (patternType < 0) {
    memset(pattern,0,40);
  }
  else {
    memset(pattern,0xff,40);
  }
}

void updateArena() {
  int i;
  SPI.beginTransaction(settingsA);
  digitalWriteFast(STCPpin, LOW);
  for (i = 0; i < 40; i++){
    SPI.transfer(pattern[i]);
  }
  delayMicroseconds(100);
  digitalWriteFast(STCPpin, HIGH);
  SPI.endTransaction();
}
