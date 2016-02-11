# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""

from .experimentCommon import *
from .dataIO import *
import DAQmxAcquisition
from .stimulus import AddExperimentToDataFile
import LEDarena

def abortExperimentOnKeypress():
    global experimentAbort
    while True:
        char = getch()
        if char == "\x08":
            experimentAbort = True
            return

def runExperiment(data_file_name, file_mode='a', 
                  experiment='full', mCalib=False, repeats=10):
    data_file = h5py.File(data_file_name, file_mode)
    global inputQ, outputQ, experimentEnd, experimentAbort
    if experiment not in data_file:
        if experiment == "mCalib":
            protocol_string = "mec(4,5,4,[0,120/120,0],0.4)"
            randomize = False
        elif experiment == "full":
            protocol_string = '''
    vis(4,5,4,10,[0/1/2/3],40);
    vis(4,8,4,10,[4/5],40);
    vic(4,5,4,10,[0/1/2/3],[0,100/100,0]);
    mep(4,[0.02,4.08/0.1,4/0.5,4],0.4);
    men(4,5,4,120,0.4);
    mec(4,5,4,[0,120/120,0],0.4);
    mcv(4,5,5,0,4,[0,120/120,0],0.4,10,[0/1/2/3],40);
    mcv(4,8,8,0,4,[0,120/120,0],0.4,10,[4/5],40);
    '''
            randomize = True
        elif experiment == "brb":
            protocol_string = "brb(100)"
            randomize = False
        elif experiment == "dyeN":
            protocol_string = "dye(60,3)"
            randomize = False
        elif experiment == "dyeL":
            protocol_string = "dye(60,5)"
            randomize = False
        else:
            protocol_string = raw_input("Enter protocol string:")
            randomize = raw_input("Randomize?(y/n): ")
            if randomize.lower() in ["y", "yes"]:
                randomize = True
            else:
                randomize = False
    
        AddExperimentToDataFile(data_file_name, experiment_name=experiment,
                                protocol_string=expandStimulusRepresentation(protocol_string), 
                                randomize=randomize, mCalib=mCalib, repeats=repeats)
    LED_arena = LEDarena.arena('com7')
    LED_arena.setBrightness(arena_brightness_percent)
    
    for item in [experiment, "warmup", "cooldown"]:
        if item not in data_file:
            data_file.copy(stimulus_master_file[item], data_file)
    
    data_file.close()
        
    data_file = h5py.File(data_file_name, 'a')
    experiment_ref = data_file[experiment]
    experiment_ref.attrs["Arena: Brightness percent"] = arena_brightness_percent
    experiment_duration = experiment_ref.attrs["Trial End Point List"][-1] / sampling_rate
    
    DAQ = DAQmxAcquisition.Continuous(ai="Dev1/ai0:2",
                                      ao="Dev1/ao0:1",
                                      di="Dev1/port0/line2:3",
                                      do="Dev1/port0/line0:1")
    
    thread.start_new_thread(readStimulus, (experiment_ref, ))
    thread.start_new_thread(writeData, (experiment_ref, data_file))
    
    thread.start_new_thread(abortExperimentOnKeypress, tuple())
    
    while True:
        if experimentAbort:
            break
        try:
            output_item = outputQ.get(block=True,timeout=0.1)
        except Queue.Empty:
            if inputQ.empty():
                break
            else:
                continue
        if output_item.new_protocol:
            data_file.flush()
            LED_arena.sendPattern(angular_size=int(output_item.arena_angular_size),
                                  mode=output_item.arena_mode)
            print "\nDone", secondsToHMS((output_item.read_till - sample_section) / sampling_rate),
            print "of", secondsToHMS(experiment_duration)        
            print "Current Protocol:", output_item.protocol_name.split('/')[-1], 
            print "Duration:", output_item.protocol_duration
            
        input_item = inputItem()
        input_item.analog_in, input_item.digital_in = \
            DAQ.acquire(output_item.analog_out, output_item.digital_out)
        if len(input_item.analog_in) > 0:
            inputQ.put_nowait(input_item)
    
    temp1, temp2 = DAQ.acquire(dataArray(), dataArray(digital=True))
    DAQ.stop()
    data_file.flush()
    data_file.close()
    LED_arena._end()
    return experimentAbort, experimentEnd

# vim: set ts=4 sw=4 ft=python ai nu et
