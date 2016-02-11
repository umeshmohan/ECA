# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)

Requirements : DAQmx (full / core + header file)
               PyDAQmx
               numpy
Written for NI USB-6229 / USB-6259
"""

from .experimentCommon import *
from PyDAQmx import *

class Continuous:
    """Continuous, Synchronized Analog & Digital[!] Input-Output

    [!] Digital input task does not support start trigger. So digital input
    data will be offset by an unknown number of samples. Use two extra
    digital lines with hardware loopback to figure out the offset.
    """
    def __init__(self, ai=None, ao=None, di=None, do=None,
                 n_samples_section=1000):
        global sampling_rate
        self.bufferSize = uInt32(int(sampling_rate))
        self.n_samples_section = n_samples_section
        self.read = None
        self.written = None
        self.ai_n_samples_read = 0
        self.di_n_samples_read = 0
        self._analogRead = int32()
        self._digitalRead = int32()
        self._digitalReadBytes = int32()
        self._analogWritten = int32()
        self._digitalWritten = int32()
        try:
            if ao is not None:
                self.ao_task_handle = TaskHandle()
                DAQmxCreateTask("AO", byref(self.ao_task_handle))
                DAQmxCreateAOVoltageChan(self.ao_task_handle, ao, "", 
                                         -10.0, 10.0, DAQmx_Val_Volts, None)
                DAQmxCfgSampClkTiming(self.ao_task_handle, "OnboardClock", 
                                      sampling_rate, DAQmx_Val_Rising, 
                                      DAQmx_Val_ContSamps, 
                                      self.n_samples_section)
                DAQmxCfgOutputBuffer(self.ao_task_handle, self.bufferSize)
                DAQmxSetWriteRegenMode(self.ao_task_handle, 
                                       DAQmx_Val_DoNotAllowRegen)
                self.ao_chan_count = countChannels(ao)
            else:
                self.ao_task_handle = None
                self.ao_chan_count = None
            if do is not None:
                self.do_task_handle = TaskHandle()
                DAQmxCreateTask("DO", byref(self.do_task_handle))
                DAQmxCreateDOChan(self.do_task_handle, do, "", 
                                  DAQmx_Val_ChanForAllLines)
                DAQmxCfgSampClkTiming(self.do_task_handle, "ao/SampleClock", 
                                      sampling_rate, DAQmx_Val_Rising, 
                                      DAQmx_Val_ContSamps, 
                                      self.n_samples_section)
                DAQmxCfgOutputBuffer(self.do_task_handle, self.bufferSize)
                DAQmxSetWriteRegenMode(self.do_task_handle, 
                                       DAQmx_Val_DoNotAllowRegen)
                self.do_chan_count = countChannels(do)
            else:
                self.do_task_handle = None
                self.ao_chan_count = None
            if ai is not None:
                self.ai_task_handle = TaskHandle()
                DAQmxCreateTask("AI", byref(self.ai_task_handle))
                DAQmxCreateAIVoltageChan(self.ai_task_handle, ai, "", 
                                         DAQmx_Val_Cfg_Default, -10.0, 10.0, 
                                         DAQmx_Val_Volts, None)
                DAQmxCfgSampClkTiming(self.ai_task_handle, "ao/SampleClock", 
                                      sampling_rate, DAQmx_Val_Rising, 
                                      DAQmx_Val_ContSamps, 
                                      self.n_samples_section)
                DAQmxCfgDigEdgeStartTrig(self.ai_task_handle, 
                                         "ao/StartTrigger", DAQmx_Val_Rising)
                DAQmxCfgInputBuffer(self.ai_task_handle, self.bufferSize)
                DAQmxSetReadOverWrite(self.ai_task_handle, 
                                      DAQmx_Val_DoNotOverwriteUnreadSamps)
                DAQmxStartTask(self.ai_task_handle)
                self.ai_chan_count = countChannels(ai)
            else:
                self.ai_task_handle = None
                self.ai_chan_count = None
            if di is not None:
                self.di_task_handle = TaskHandle()
                DAQmxCreateTask("DI", byref(self.di_task_handle))
                DAQmxCreateDIChan(self.di_task_handle, di, "", 
                                  DAQmx_Val_ChanForAllLines)
                DAQmxCfgSampClkTiming(self.di_task_handle, "ao/SampleClock", 
                                      sampling_rate, DAQmx_Val_Rising, 
                                      DAQmx_Val_ContSamps, 
                                      self.n_samples_section)
#                print "Warning! Digital input task does not support start \
#trigger. So digital input data will be offset by an unknown number of samples\
#. Use two extra digital lines with hardware loopback to figure out the offset."
                DAQmxCfgInputBuffer(self.di_task_handle, self.bufferSize)
                DAQmxSetReadOverWrite(self.di_task_handle, 
                                      DAQmx_Val_DoNotOverwriteUnreadSamps)
                DAQmxStartTask(self.di_task_handle)
                self.di_chan_count = countChannels(di)
            else:
                self.di_task_handle = None
                self.di_chan_count = None
        except DAQError as err:
            print "DAQmx Error in Initializing: %s"%err
            self.stop()

    def acquire(self, ao_data, do_data):
        try:
            if self.ao_task_handle is not None:
                DAQmxWriteAnalogF64(self.ao_task_handle, 
                                    self.n_samples_section, 1, 10.0, 
                                    DAQmx_Val_GroupByScanNumber, 
                                    ao_data, byref(self._analogWritten), None)
                self.written = self._analogWritten.value
            if self.do_task_handle is not None:
                DAQmxWriteDigitalLines(self.do_task_handle, 
                                       self.n_samples_section, 1, 10.0, 
                                       DAQmx_Val_GroupByScanNumber, 
                                       do_data, byref(self._digitalWritten), 
                                       None)
            if self.ai_task_handle is not None:
                ai_data = dataArray((self.n_samples_section,
                                      self.ai_chan_count))
                DAQmxReadAnalogF64(self.ai_task_handle, -1, 10.0, 
                                   DAQmx_Val_GroupByScanNumber, 
                                   ai_data, ai_data.size, 
                                   byref(self._analogRead), None)
                self.read = self._analogRead.value
                self.ai_n_samples_read += self._analogRead.value
            else:
                ai_data = None
            if self.di_task_handle is not None:
                di_data = dataArray((self.n_samples_section,
                                      self.di_chan_count), digital=True)
                DAQmxReadDigitalLines(self.di_task_handle, -1, 10.0, 
                                      DAQmx_Val_GroupByScanNumber,
                                      di_data,di_data.size, 
                                      byref(self._digitalRead), 
                                      byref(self._digitalReadBytes), None)
                self.di_n_samples_read += self._digitalRead.value
            else:
                di_data = None
        except DAQError as err:
            print "DAQmx Error in acquire: %s"%err
            self.stop()
        return ai_data[:self.read], di_data[:self.read]

    def stop(self):
        for taskHandle in [self.ai_task_handle, self.ao_task_handle,
                           self.di_task_handle, self.do_task_handle]:
            if taskHandle is not None:
                DAQmxStopTask(taskHandle)
                DAQmxClearTask(taskHandle)

def countChannels(channelString=""):
    """Returns the number of physical channels in a string containing
    physical channel lists

    http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/physchannames/
    """
    count = 0
    if channelString.count(",") > 0:
        t = channelString.split(",")
        for i in t:
            count += countChannels(i)
        return count
    else:
        if channelString.count(":") > 0:
            t2 = channelString.split(":")
            n2 = int(t2[1])
            # Detect last number in string:
            t3 = re.match(r'(.*?)(\d+$)', t2[0]).groups() 
            n1 = int(t3[1])
            if n1 > n2:
                return n1 - n2 + 1
            else:
                return n2 - n1 + 1
        else:
            return 1

if __name__ == "__main__":
    sampling_rate = 10000
    ao = dataArray((80000,2))
    do = dataArray((80000,2), digital=True)

    f0=0
    f1=23
    T=5.0
    k=(f1-f0)/T
    for i in range(10000,60000):
        t = (i-10000)/10000.0
        t2 = math.sin(2.0*math.pi*t*(1+((k/2)*t)))
        if t2 > 0:
            do[i][0] = 1
            do[i][1] = 1
        else:
            do[i][0] = 0
            do[i][1] = 0
        ao[i][0] = t2
        ao[i][1] = ao[i][0]*2



    test = Continuous(ai="Dev1/ai0:1", ao="Dev1/ao0:1",
                      di="Dev1/port0/line2:3", do="Dev1/port0/line0:1")

    ai = dataArray((0,2))
    di = dataArray((0,2), digital=True)
    for i in range(80):
        print i,
        ao_section = ao[i*1000:(i+1)*1000,]
        do_section = do[i*1000:(i+1)*1000,]
        if i>10:
            time.sleep(test.n_samples_section/(1.3*sampling_rate))

        ai, di = test.acquire(ao_section, do_section)

        print 'Witten', test.written, "Read", test.read, "samples"
    print "Total samples read:", test.ai_n_samples_read, test.di_n_samples_read

    test.stop()
    del test
# vim: set ts=4 sw=4 ft=python ai nu et
