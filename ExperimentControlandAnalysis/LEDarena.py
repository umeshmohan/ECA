# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)

Requirements : pyserial

Written for 1D LED arena vI.2
"""

from .experimentCommon import thread, math
import serial

class arena:
    def __init__(self, port):
        self._serial = serial.Serial(port=port, baudrate=115200, timeout=0.05)
        self.readall()

    def setBrightness(self, percent):
        max_brightness = (2 ** 16) - 1
        if percent < 100:
            brightness = (int((math.log10(100 - percent) / 2) * max_brightness))
        else:
            brightness = 0
        command=[0xcc, 0x01, brightness & 0xff, (brightness & 0xff00) >> 8]
        self._write(command)
        self.readall()
    
    def sendPattern(self, mode="forward", angular_size=10):
        mode_list = ["forward", "backward", "clockwise", "counterclockwise", 
                     "spot clockwise", "spot counterclockwise"]
        pattern_type = mode_list.index(mode)
        command = [0xcc, 0x02, 
                   pattern_type & 0xff, (pattern_type & 0xff00) >> 8, 
                   angular_size & 0xff, (angular_size & 0xff00) >> 8]
        self._write(command)
        self.readall()

    def end(self):
        thread.start_new_thread(self._end,())

    def _end(self):
        #self._readall()
        self._serial.close()

    def readall(self):
        thread.start_new_thread(self._readall,())

    def _readall(self):
        print self._serial.readall()

    def _write(self,data):
        thread.start_new_thread(self._serial.write,(data,))

# vim: set ts=4 sw=4 ft=python ai nu et
