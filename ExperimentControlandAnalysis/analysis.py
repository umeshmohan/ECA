# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""
import numpy as np
import scipy.signal
from scipy.ndimage.filters import gaussian_filter1d

def Filter(signal, f, f_pass='lowpass', poles=10, sampling_rate = 10000):
    normalized_f = f / (0.5 * sampling_rate)
    b, a = scipy.signal.butter(poles, normalized_f, btype=f_pass, analog=False)
    return scipy.signal.filtfilt(b, a, signal)

def GetSpikePositionList(signal):
    noise_level = np.std(signal)
    max_point = np.max(signal)
    threshold = (max_point + (np.mean(signal) + noise_level)) / 2
    spike = np.diff((signal > threshold) * 1) > 0
    tentative_spike_position_list = 1 + np.argwhere(spike)
    spike_position_list = np.zeros(len(tentative_spike_position_list))
    for i in range(len(tentative_spike_position_list)):
        spike_position_list[i] = (tentative_spike_position_list[i] - (10 - 
            _GetSpikeInitiationPoint(signal[tentative_spike_position_list[i] - 
                10:tentative_spike_position_list[i]], noise_level)))
    return spike_position_list

def _GetSpikeInitiationPoint(signal_section, noise_level):
    temp = np.where((signal_section > noise_level) == False)[0]
    if len(temp) == 0:
        return len(signal_section) - 1
    else:
        return temp[-1]

def SpikePositionListListToPreGCFR(spike_position_list_list, length):
    pre_GCFR = np.zeros(length)
    for spike_position_list in spike_position_list_list:
        for spike_position in spike_position_list:
            pre_GCFR[spike_position] += 1
    return pre_GCFR

def SpikePositionListListToArray(spike_position_list_list):
    max_n_spikes = 0
    spike_position_array = None
    for spike_position_list in spike_position_list_list:
        if len(spike_position_list) > max_n_spikes:
            max_n_spikes = len(spike_position_list)
    for spike_position_list in spike_position_list_list:
        if len(spike_position_list) < max_n_spikes:
            temp = np.concatenate((spike_position_list,
                                   np.zeros(max_n_spikes - \
                                            len(spike_position_list))-1))
        else:
            temp = spike_position_list
        if spike_position_array is None:
            spike_position_array = temp
        else:
            spike_position_array = np.vstack((spike_position_array, temp))
    return spike_position_array

#def GCFR(pre_GCFR, sigma):
#    return gaussian_filter1d(pre_GCFR, sigma)
GCFR = gaussian_filter1d

def __VtoD__(v):
    d = ((211.8 / (v - 1.506)) ** (1.0 / 3.0)) - 2.075
    return d

hallEffectSensorToDisplacement = np.vectorize(__VtoD__, otypes=[np.float])

def mec_hallEffectSensorToDisplacementAmplitude(mec_hall_effect_sensor_reading,
                                                mec_parameters=[4, 5, 4, 0, 120, 0.4]):
    global sampling_rate
    pre_stimulus_delay = mec_parameters[0]
    stimulus_duration = mec_parameters[1]
    post_stimulus_delay = mec_parameters[2]
    frequency_0 = mec_parameters[3]
    frequency_1 = mec_parameters[4]
    antenna_displacement = hallEffectSensorToDisplacement(mec_hall_effect_sensor_reading)
    #antenna_displacement = mec_hall_effect_sensor_reading
    reverse = False;
    if frequency_0 > frequency_1:
        frequency_1, frequency_0 = frequency_0, frequency_1
        antenna_displacement = antenna_displacement[::-1]
        reverse = True;
    amplitude = mec_parameters[5]
    antenna_displacement = antenna_displacement - antenna_displacement[0]
    antenna_displacement = antenna_displacement[
        pre_stimulus_delay * sampling_rate:
        (pre_stimulus_delay + stimulus_duration) * sampling_rate]
    if frequency_0 > frequency_1:
        f_cut=frequency_0
    else:
        f_cut=frequency_1    
    b, a = scipy.signal.butter(10, (f_cut * 4.0) / 5000, btype='low', analog=False)
    antenna_displacement = scipy.signal.filtfilt(b, a, antenna_displacement)    
    b, a = scipy.signal.butter(3, 0.2 / 5000, btype='high', analog=False)
    antenna_displacement = scipy.signal.filtfilt(b, a, antenna_displacement)    
    chirp = stimulus._chirp(stimulus_duration,
                        frequency_0=frequency_0,
                        frequency_1=frequency_1)
    t = chirp > 0
    t = np.diff(t)
    t = np.nonzero(t)
    wave_end_point_list = t[0][::2]
    previous_point = 0
    amplitude_dict = {}
    i = 0
    #pg.plot(antenna_displacement)
    for current_point in wave_end_point_list[1:]:
        wave = antenna_displacement[previous_point:current_point]
        frequency = 10000.0 / (current_point - previous_point)
        current_wave_amplitude = np.max(wave) - np.min(wave)
        if frequency in amplitude_dict:
            amplitude_dict[frequency].append(current_wave_amplitude)
            ##print wave
        else:
            amplitude_dict.update({frequency: [current_wave_amplitude]})
        i += 1
        previous_point = current_point
    frequency_list = amplitude_dict.keys()
    frequency_list.sort()
    amplitude_list = []
    for frequency in frequency_list:
        amplitude_list.append(np.mean(amplitude_dict[frequency]))
    b, a = scipy.signal.butter(10, 0.2, btype='low', analog=False)
    amplitude_list = scipy.signal.filtfilt(b, a, amplitude_list)
    #pg.plot(amplitude_list, title="amplitude_list")
    t = np.linspace(0, frequency_1, (stimulus_duration * sampling_rate) + 1)
    t = t[:stimulus_duration * sampling_rate]
    print mec_parameters
    ##print amplitude_list
    amplitude_list = np.interp(t, frequency_list, amplitude_list) / 2
    if reverse:
        amplitude_list = amplitude_list[::-1]
        antenna_displacement = antenna_displacement[::-1]
    #pg.plot(amplitude_list, title="amplitude_list interp")
    ##print amplitude_list,frequency_list
    #if frequency_0 > frequency_1:
    #    amplitude_list = amplitude_list / amplitude_list[0]
    #else:
    #    amplitude_list = amplitude_list / amplitude_list[0]
    ##print "mec parameters", mec_parameters
    ##print t.size,amplitude_list.size
    ##print np.mean(mec_hall_effect_sensor_reading), np.std(mec_hall_effect_sensor_reading)
    ##print np.mean(antenna_displacement), np.std(antenna_displacement)
    correction = 1/amplitude_list
    #pg.plot(correction, title="correction")
    #print correction, min(correction), max(correction)
    correction = correction / correction[0]
    #pg.plot(correction, title="correction normalized")
    #print correction, min(correction), max(correction)
    c=chirp*correction
    #pg.plot(c, title="corrected")
    #raw_input()
    return correction
