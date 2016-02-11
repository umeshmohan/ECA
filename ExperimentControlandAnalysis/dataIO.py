# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)

Requirements : 

# Analog out:
#            0: To Amplifier EXT I
#            1: To Speaker

# Digital out:
#  Port0/line0: To Amplifier GATE
#            1: To LED arena - next in sequence

# Analog in:
#            0: From Amplifier 10Vm
#            1: From Amplifier I MON
#            2: From Hall Effect Sensor

# Digital in:
#  Port0/line2: Loop back from Port0/line1 
#            3: STCP
"""
from .experimentCommon import *

def readStimulus(experiment_ref):
    global outputQ, experimentEnd, experimentAbort, sample_section
    experimentEnd = False
    read_till = 0
    read_max = experiment_ref.attrs["Trial End Point List"][-1]
    while True:
        if experimentAbort or experimentEnd:
            print "readStimulus: experimentAbort:", experimentAbort, \
                  "experimentEnd:", experimentEnd, "\n exiting readStimulus"
            #outputQ.task_done()
            return
        protocol_list = experiment_ref.attrs["Protocol List"]
        trial_end_point_list = experiment_ref.attrs["Trial End Point List"]
        sample_point_start = read_till
        protocol, protocol_sample_start, protocol_sample_end = \
            samplePointToProtocol(protocol_list, trial_end_point_list,
                              sample_point_start, sample_section)
        #print "read till:", read_till, protocol, protocol_sample_start, protocol_sample_end
        output_item = outputItem()
        if len(protocol) == 1:
            output_item.analog_out = experiment_ref[protocol[0]][
                "Analog Out"][protocol_sample_start:protocol_sample_end]
            output_item.digital_out = experiment_ref[protocol[0]][
                "Digital Out"][protocol_sample_start:protocol_sample_end]
            if protocol_sample_start == 0:
                output_item.new_protocol = True
            else:
                output_item.new_protocol = False
        else:
            a1 = experiment_ref[protocol[0]]["Analog Out"][
                protocol_sample_start:]
            a2 = experiment_ref[protocol[1]]["Analog Out"][
                :protocol_sample_end]
            d1 = experiment_ref[protocol[0]]["Digital Out"][
                protocol_sample_start:]
            d2 = experiment_ref[protocol[1]]["Digital Out"][
                :protocol_sample_end]
            output_item.analog_out = np.concatenate((a1, a2))
            output_item.digital_out = np.concatenate((d1, d2))
            output_item.new_protocol = True
        if output_item.new_protocol:
            #print "readStimulus: new_protocol set to true"
            output_item.arena_angular_size = \
                experiment_ref[protocol[-1]].attrs["Arena: Angular Size"]
            output_item.arena_mode = \
                experiment_ref[protocol[-1]].attrs["Arena: Mode"]
            output_item.protocol_name = experiment_ref[protocol[-1]].name
            output_item.protocol_duration = \
                experiment_ref[protocol[-1]].attrs["Number of Samples"] / 10000
        read_till += sample_section
        output_item.read_till = read_till
        outputQ.put(output_item, timeout=3)
        if read_till == read_max:
            experimentEnd = True
            #print "readStimulus experimentEnd set to True"
        else:
            experimentEnd = False

def writeData(experiment_ref, data_file):
    global inputQ, experimentAbort, experimentEnd
    written_till = 0
    current_trial = None
    write_max = experiment_ref.attrs["Trial End Point List"][-1]
    while True:
        #print "inputq empty:", inputQ.empty()
        try:
            input_item = inputQ.get(block=True,timeout=5)
        except Queue.Empty:
            if experimentAbort or experimentEnd:
                print "Write data: experimentAbort:", experimentAbort, \
                      "experimentEnd:", experimentEnd
                #inputQ.join()
                print "exiting writeData"
                data_file.close()                
                return
        protocol_list = experiment_ref.attrs["Protocol List"]
        trial_end_point_list = experiment_ref.attrs["Trial End Point List"]
        sample_point_start = written_till
        #input_item = inputQ.get(block=True,timeout=5)
        #print input_item, input_item.analog_in, input_item.digital_in
        number_of_samples = input_item.analog_in.shape[0]
        protocol, protocol_sample_start, protocol_sample_end = \
            samplePointToProtocol(protocol_list, trial_end_point_list,
                                  sample_point_start, number_of_samples)
        if len(protocol) == 1:
            if protocol_sample_start == 0:
                current_trial = _getNextTrial(experiment_ref[protocol[0]])
            current_trial["Analog In"][
                protocol_sample_start:protocol_sample_end, :] = \
                input_item.analog_in
            current_trial["Digital In"][
                protocol_sample_start:protocol_sample_end, :] = \
                input_item.digital_in
        else:
            current_trial["Analog In"][protocol_sample_start:, :] = \
                input_item.analog_in[:-protocol_sample_start, :]
            current_trial["Digital In"][protocol_sample_start:, :] = \
                input_item.digital_in[:-protocol_sample_start, :]
            current_trial.attrs["Trial Completed"] = True
            current_trial = _getNextTrial(experiment_ref[protocol[1]])
            current_trial["Analog In"][:protocol_sample_end, :] = \
                input_item.analog_in[-protocol_sample_end:, :]
            current_trial["Digital In"][:protocol_sample_end, :] = \
                input_item.digital_in[-protocol_sample_end:, :]
        written_till += number_of_samples

def samplePointToProtocol(protocol_list, trial_end_point_list,
                          sample_point_start, number_of_samples):
    #print "samplePointToProtocol", protocol_list, trial_end_point_list, sample_point_start, number_of_samples
    sample_point_end = sample_point_start + number_of_samples
    protocol_start_number = np.searchsorted(trial_end_point_list, 
                                            sample_point_start, 
                                            side='right') - 1
    protocol_end_number = np.searchsorted(trial_end_point_list, 
                                          sample_point_end - 1, 
                                          side='right') - 1
    #print "protocol start,end:", protocol_start_number, protocol_end_number
    if protocol_start_number != protocol_end_number:
        #raise Exception("Sample section is spilling into the next protocol")
        current_protocol = [protocol_list[protocol_start_number],
                            protocol_list[protocol_end_number]]
        protocol_sample_start = int(sample_point_start -
                                    trial_end_point_list[protocol_end_number])
        protocol_sample_end = int((sample_point_start + number_of_samples) -
                                  trial_end_point_list[protocol_end_number])
    else:
        current_protocol = [protocol_list[protocol_start_number]]
        protocol_sample_start = int(sample_point_start -
                                    trial_end_point_list[protocol_start_number])
        protocol_sample_end = int(protocol_sample_start + number_of_samples)
    #print "samplePointToProtocol output", current_protocol, protocol_sample_start, protocol_sample_end
    return current_protocol, protocol_sample_start, protocol_sample_end

def _getNextTrial(protocol_ref):
    #print "Get Next Trial", protocol_ref
    protocol_contents = protocol_ref.keys()
    protocol_contents.remove("Analog Out")
    protocol_contents.remove("Digital Out")
    next_trial = "Trial-" + str(len(protocol_contents) + 1)
    next_trial_ref = protocol_ref.create_group(next_trial)
    protocol_number_of_samples = int(protocol_ref.attrs["Number of Samples"])
    next_trial_ref.create_dataset("Analog In", (protocol_number_of_samples,3),
                              dtype=np.float64, fillvalue=np.NaN, fletcher32=True)
    next_trial_ref.create_dataset("Digital In", (protocol_number_of_samples, 2),
                                  dtype=np.uint8, fillvalue=np.NaN, fletcher32=True)
    next_trial_ref.attrs["Trial Completed"] = False
    return next_trial_ref
