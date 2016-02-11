# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""
from .experimentCommon import *
from .analysis import mec_hallEffectSensorToDisplacementAmplitude
from .dataFileHandling import Protocol

# PrSD  PreStimulus Duration
# SD    Stimulus Duration
# PoSD  Post Stimulus Duration
# f     frequency
# a     amplitude
# MSD   Mechanical Stimulus Duration
# VSD   Visual Stimulus Duration
# MVD   Mechanical-Visual Delay

# Analog out:
#            0: To Amplifier EXT I
#            1: To Speaker

# Digital out:
#            0: To Amplifier GATE
#            1: To LED arena - next in sequence

dt = 1 / float(sampling_rate)

def AddExperimentToDataFile(data_file_path, experiment_name="Test",
                              protocol_string="bla(60)", 
                              randomize=True,
                              mCalib=None,
                              repeats=1):
    stimulus_master_file = h5py.File(data_file_path, 'a')
    if mCalib:
        mCalib_file = h5py.File(mCalib["file"], 'r')
        calib_exp = mCalib_file[mCalib["protocol"]]
    else:
        calib_exp = None
    if "warmup" not in stimulus_master_file:
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            _createStimulus(protocol_id="bla(5)")
        protocol = stimulus_master_file.create_group("warmup")
        protocol.attrs["Arena: Angular Size"] = arena_angular_size
        protocol.attrs["Arena: Mode"] = arena_mode
        protocol.attrs["Number of Samples"] = length
        protocol.create_dataset("Analog Out", data=analog_out, fletcher32=True)
        protocol.create_dataset("Digital Out", data=digital_out, fletcher32=True)            
    if "cooldown" not in stimulus_master_file:
        stimulus_master_file["cooldown"] = h5py.SoftLink("/warmup")
    
    if experiment_name in stimulus_master_file:
        raise Exception("Experiment present in data file")
    if experiment_name not in stimulus_master_file:
        experiment = stimulus_master_file.create_group(experiment_name)
        experiment.attrs['Title'] = experiment_name
        experiment.attrs['Protocol String'] = protocol_string
        experiment.attrs['Randomized'] = randomize
        protocol_list = protocol_string.split(';')
        if randomize:
            random.shuffle(protocol_list)
        unique_protocol_list = protocol_list[:]
        protocol_list = repeats * unique_protocol_list
        for protocol_id in unique_protocol_list:
            length, arena_angular_size, arena_mode, analog_out, digital_out = \
                _createStimulus(protocol_id=protocol_id, mCalib=calib_exp)
            protocol = experiment.create_group(protocol_id)
            protocol.attrs["Arena: Angular Size"] = arena_angular_size
            protocol.attrs["Arena: Mode"] = arena_mode
            protocol.attrs["Number of Samples"] = length
            protocol.create_dataset("Analog Out", data=analog_out, fletcher32=True)
            protocol.create_dataset("Digital Out", data=digital_out, fletcher32=True)
        experiment["warmup"] = h5py.SoftLink("/warmup")
        experiment["cooldown"] = h5py.SoftLink("/cooldown")
        protocol_list = ["warmup"] + protocol_list + ["cooldown"]
        experiment.attrs['Protocol List'] = protocol_list
        trial_end_point_list = [0]
        for protocol in protocol_list:
            trial_end_point_list.append(trial_end_point_list[-1] + \
                experiment[protocol].attrs["Number of Samples"])
        experiment.attrs["Trial End Point List"] = trial_end_point_list
    stimulus_master_file.close()
    if mCalib:
        mCalib_file.close()

def _createStimulus(protocol_id="bla(60)", mCalib=None):
    t = protocol_id.split("(")
    protocol_type = t[0]
    protocol_parameters = []
    for parameter in t[1][:-1].split(','):
        protocol_parameters.append(float(parameter))
    if protocol_type == "bla":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            blank(protocol_parameters)
    elif protocol_type == "brb":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            bridgeBalance(protocol_parameters)
    elif protocol_type == "mep":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalPulse(protocol_parameters)
    elif protocol_type == "mes":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalSine(protocol_parameters)
    elif protocol_type == "mec":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalChirp(protocol_parameters,mCalib=mCalib)
    elif protocol_type == "men":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalNoise(protocol_parameters)
    elif protocol_type == "vis":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            visual(protocol_parameters)
    elif protocol_type == "vic":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            visualChirp(protocol_parameters)
    elif protocol_type == "msv":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalSineAndVisual(protocol_parameters)
    elif protocol_type == "mcv":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            mechanicalChirpAndVisual(protocol_parameters,mCalib=mCalib)
    elif protocol_type == "dye":
        length, arena_angular_size, arena_mode, analog_out, digital_out = \
            dye(protocol_parameters)
    else:
        raise NotImplementedError("Stimulus " + protocol_type +
                                  " not implemented")
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def blank(parameters):
    global sampling_rate
    _protocolParameterCheck("Blank", 1, parameters)
    [SD] = parameters
    length = _roundoff(SD * sampling_rate)
    analog_out = dataArray(shape=(length, 2))
    digital_out = dataArray(shape=(length, 2), digital=True)
    arena_angular_size = 10
    arena_mode = "forward"
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def bridgeBalance(parameters):
    global sampling_rate
    _protocolParameterCheck("Bridge Balance", 1, parameters)
    [SD] = parameters
    length = _roundoff(SD * sampling_rate)
    temp, arena_angular_size, arena_mode, analog_out, digital_out = \
        blank([SD])
    analog_out[:, 0] = 0.05 * _squareWave(SD, frequency=3, digital=False)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalPulse(parameters):
    global sampling_rate
    _protocolParameterCheck("Mechanical Pulse", 4, parameters)
    [PrSD, SD, PoSD, amplitude] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp, arena_angular_size, arena_mode, analog_out, digital_out = \
        blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    analog_out[stimulus_start_n:stimulus_stop_n, 1] = \
        amplitude * np.ones((SD * sampling_rate), dtype=np.float64)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalSine(parameters):
    global sampling_rate
    _protocolParameterCheck("Mechanical Sine", 5, parameters)
    [PrSD, SD, PoSD, frequency, amplitude] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp, arena_angular_size, arena_mode, analog_out, digital_out = \
        blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    analog_out[stimulus_start_n:stimulus_stop_n, 1] = \
        amplitude * _sineWave(SD, frequency=frequency)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalChirp(parameters,mCalib=None):
    global sampling_rate
    _protocolParameterCheck("Mechanical Chirp", 6, parameters)
    [PrSD, SD, PoSD, frequency_0, frequency_1, amplitude] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp, arena_angular_size, arena_mode, analog_out, digital_out = \
        blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    analog_out[stimulus_start_n:stimulus_stop_n, 1] = \
        _chirp(SD, frequency_0=frequency_0, frequency_1=frequency_1,
               amplitude=amplitude, mCalib=mCalib)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalNoise(parameters):
    global sampling_rate
    _protocolParameterCheck("Mechanical Noise", 5, parameters)
    [PrSD, SD, PoSD, frequency_0, amplitude] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp, arena_angular_size, arena_mode, analog_out, digital_out = \
        blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    analog_out[stimulus_start_n:stimulus_stop_n, 1] = \
        _noise(SD, frequency_0=frequency_0, amplitude=amplitude*4)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def visual(parameters):
    global sampling_rate
    _protocolParameterCheck("Visual", 6, parameters)
    [PrSD, SD, PoSD, arena_angular_size, mode, arena_speed] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp1, temp2, temp3, analog_out, digital_out = blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    digital_out[stimulus_start_n:stimulus_stop_n, 1] = \
        _squareWave(SD, frequency=arena_speed)
    if mode == 0:
        arena_mode = "forward"
    elif mode == 1:
        arena_mode = "backward"
    elif mode == 2:
        arena_mode = "clockwise"
    elif mode == 3:
        arena_mode = "counterclockwise"
    elif mode == 4:
        arena_mode = "spot clockwise"
    elif mode == 5:
        arena_mode = "spot counterclockwise"
    else:
        raise NotImplementedError("Arena mode not implemented - mode: " +
                                  str(mode))
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def visualChirp(parameters):
    global sampling_rate
    _protocolParameterCheck("Visual Chirp", 7, parameters)
    [PrSD, SD, PoSD, arena_angular_size, mode, arena_speed_0, arena_speed_1] = parameters
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp1, temp2, temp3, analog_out, digital_out = blank([PrSD + SD + PoSD])
    stimulus_start_n = PrSD * sampling_rate
    stimulus_stop_n = stimulus_start_n + (SD * sampling_rate)
    temp = _chirp(SD, frequency_0=arena_speed_0, frequency_1=arena_speed_1, amplitude=1)
    temp = temp > 0
    digital_out[stimulus_start_n:stimulus_stop_n, 1] = temp.astype(np.uint8)
    if mode == 0:
        arena_mode = "forward"
    elif mode == 1:
        arena_mode = "backward"
    elif mode == 2:
        arena_mode = "clockwise"
    elif mode == 3:
        arena_mode = "counterclockwise"
    else:
        raise NotImplementedError("Arena chirp mode not implemented - mode: " +
                                  str(mode))
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalSineAndVisual(parameters):
    global sampling_rate
    _protocolParameterCheck("Mechanical Sine + Visual", 10, parameters)
    [PrSD, MSD, VSD, MVD, PoSD, frequency, amplitude, arena_angular_size,
     mode, arena_speed] = parameters
    if MVD == 0:
        SD = max(MSD, VSD)
        mechanical_stimulus_start_n = PrSD * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = mechanical_stimulus_start_n
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    elif MVD > 0:
        SD = max(MSD, VSD + MVD)
        mechanical_stimulus_start_n = PrSD * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = mechanical_stimulus_start_n + \
            (MVD * sampling_rate)
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    else:
        SD = max(MSD - MVD, VSD)
        mechanical_stimulus_start_n = (PrSD - MVD) * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = PrSD * sampling_rate
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp1, temp2, temp3, analog_out, digital_out = blank([PrSD + SD + PoSD])
    digital_out[visual_stimulus_start_n:visual_stimulus_stop_n, 1] = \
        _squareWave(VSD, frequency=arena_speed)
    analog_out[mechanical_stimulus_start_n:mechanical_stimulus_stop_n, 1] = \
        amplitude * _sineWave(MSD, frequency=frequency)
    if mode == 0:
        arena_mode = "forward"
    elif mode == 1:
        arena_mode = "backward"
    elif mode == 2:
        arena_mode = "clockwise"
    elif mode == 3:
        arena_mode = "counterclockwise"
    elif mode == 4:
        arena_mode = "spot clockwise"
    elif mode == 5:
        arena_mode = "spot counterclockwise"
    else:
        raise NotImplementedError("Arena mode not implemented - mode: " +
                                  str(mode))
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def mechanicalChirpAndVisual(parameters,mCalib=None):
    global sampling_rate
    _protocolParameterCheck("Mechanical Chirp + Visual", 11, parameters)
    [PrSD, MSD, VSD, MVD, PoSD, frequency_0, frequency_1, amplitude,
     arena_angular_size, mode, arena_speed] = parameters
    if MVD == 0:
        SD = max(MSD, VSD)
        mechanical_stimulus_start_n = PrSD * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = mechanical_stimulus_start_n
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    elif MVD > 0:
        SD = max(MSD, VSD + MVD)
        mechanical_stimulus_start_n = PrSD * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = mechanical_stimulus_start_n + \
            (MVD * sampling_rate)
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    else:
        SD = max(MSD - MVD, VSD)
        mechanical_stimulus_start_n = (PrSD - MVD) * sampling_rate
        mechanical_stimulus_stop_n = mechanical_stimulus_start_n + \
            (MSD * sampling_rate)
        visual_stimulus_start_n = PrSD * sampling_rate
        visual_stimulus_stop_n = visual_stimulus_start_n + (VSD * sampling_rate) 
    length = _roundoff((PrSD + SD + PoSD) * sampling_rate)
    temp1, temp2, temp3, analog_out, digital_out = blank([PrSD + SD + PoSD])
    digital_out[visual_stimulus_start_n:visual_stimulus_stop_n, 1] = \
        _squareWave(VSD, frequency=arena_speed)
    analog_out[mechanical_stimulus_start_n:mechanical_stimulus_stop_n, 1] = \
        _chirp(MSD, frequency_0=frequency_0, amplitude=amplitude,
                           frequency_1=frequency_1,mCalib=mCalib)
    if mode == 0:
        arena_mode = "forward"
    elif mode == 1:
        arena_mode = "backward"
    elif mode == 2:
        arena_mode = "clockwise"
    elif mode == 3:
        arena_mode = "counterclockwise"
    elif mode == 4:
        arena_mode = "spot clockwise"
    elif mode == 5:
        arena_mode = "spot counterclockwise"
    else:
        raise NotImplementedError("Arena mode not implemented - mode: " +
                                  str(mode))
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def dye(parameters):
    global sampling_rate
    _protocolParameterCheck("dye", 2, parameters)
    [SD, frequency] = parameters
    length = _roundoff(SD * sampling_rate)
    length, arena_angular_size, arena_mode, analog_out, digital_out = blank([SD])
    digital_out[:, 0] = _squareWave(SD, frequency=frequency)
    return length, arena_angular_size, arena_mode, analog_out, digital_out

def _squareWave(duration, frequency=1, duty_cycle=0.5, digital=True):
    global sampling_rate
    length = int(duration * sampling_rate)
    t = np.linspace(0, duration, duration * sampling_rate, endpoint=False)
    square_wave = (0.5 * scipy.signal.square(2 * np.pi * frequency * t)) + 0.5
    if digital:
        return square_wave.astype(np.uint8)
    else:
        return square_wave.astype(np.float64)

def _sineWave(duration, frequency=15):
    global sampling_rate, dt
    T = np.arange(0, duration, dt)
    sine_wave = np.sin(2 * np.pi * frequency * T)
    return sine_wave.astype(np.float64)

def _chirp(duration, frequency_0=0, frequency_1=120, amplitude=0.4, mCalib=None):
    global sampling_rate, dt
    k = (frequency_1 - frequency_0) / duration
    T = np.arange(0, duration, dt)
    chirp = np.asarray([np.sin(2 * np.pi * (frequency_0 * t + ((k / 2) * (t ** 2))))
             for t in T], dtype=np.float64)
    if mCalib is not None:
        mCalib_list = mCalib.keys()
        for protocol in mCalib_list:
            t = protocol.split("(")
            protocol_type = t[0]
            if protocol_type != 'mec':
                continue
            protocol_parameters = []
            for parameter in t[1][:-1].split(','):
                protocol_parameters.append(float(parameter))
            if protocol_parameters[1] == duration and \
               protocol_parameters[3] == frequency_0 and \
               protocol_parameters[4] == frequency_1 and \
               protocol_parameters[5] == amplitude:
                   chirp_protocol = Protocol(mCalib)
                   resonance_correction = \
                       mec_hallEffectSensorToDisplacementAmplitude(\
                           chirp_protocol['Processed Data']\
                                         ['Mean Antennal Movement'],
                           mec_parameters=protocol_parameters)
                   #print chirp.size, resonance_correction.size
                   #print duration, frequency_0, frequency_1, amplitude
                   chirp=chirp*resonance_correction
                   break
    return chirp * amplitude

def _noise(duration, frequency_0, amplitude):
    global sampling_rate, dt
    sample_size = sampling_rate * duration * 3
    white_noise = np.random.random(sample_size)
    white_noise =  (2 * amplitude * (white_noise - np.mean(white_noise)))
    print np.mean(white_noise), np.max(white_noise), np.min(white_noise)
    normalized_f_0 = frequency_0 / (0.5 * sampling_rate)
    b, a = scipy.signal.butter(10, normalized_f_0, btype='low', analog=False)
    band_limited_white_noise = scipy.signal.filtfilt(b, a, white_noise)
    return band_limited_white_noise[sample_size/3:2*sample_size/3].astype(np.float64)

def _roundoff(length):
    if length < 1000:
        length = 1000
    return length

def _protocolParameterCheck(protocol, number_of_parameters_needed, parameters):
    if len(parameters) != number_of_parameters_needed:
        raise Exception("Protocol " + protocol + " requires " +
                        str(number_of_parameters_needed)+ "parameter(s). Got " +
                        str(parameters))        
