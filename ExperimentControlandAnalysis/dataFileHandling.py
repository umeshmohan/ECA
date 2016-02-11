# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""

from .common import np
import h5py
from .analysis import Filter, \
                      GetSpikePositionList, \
                      SpikePositionListListToPreGCFR, \
                      SpikePositionListListToArray, \
                      hallEffectSensorToDisplacement

def GetSubGroupList(group):
    sub_group_list =  [sub_group for sub_group in group]
    for sub_group in ['cooldown', 'dye', 'warmup', 
                      'Analog Out', 'Digital Out',
                      'Processed Data']:
        while sub_group in sub_group_list:
            sub_group_list.remove(sub_group)
    for sub_group in sub_group_list:
        try:
            _ = group[sub_group].attrs.items()
        except KeyError:
            sub_group_list.remove(sub_group)
    return sub_group_list


class NeuronData:
    def __init__(self, data_file_name, reanalyze=False):
        if reanalyze:
            self._file_handle = h5py.File(data_file_name, 'a')
        else:
            self._file_handle = h5py.File(data_file_name, 'r')
            try :
                if not self._file_handle.attrs.get('Processed'):
                    reanalyze = True
                    self._file_handle.close()
                    self._file_handle = h5py.File(data_file_name, 'a')
            except KeyError:
                reanalyze = True
                self._file_handle.close()
                self._file_handle = h5py.File(data_file_name, 'a')
        self.experiment_list = self.GetExperimentList()
        self.PopulateExperiments(reanalyze=reanalyze)
        if self._file_handle.mode != 'r':
            self._file_handle.attrs.create('Processed', True)
        
        
    def close(self):
        self._file_handle.close()
    
    def GetExperimentList(self):
        return GetSubGroupList(self._file_handle)
    
    def PopulateExperiments(self, reanalyze=False):
        print("Populating Experiments, reanalyze= " + str(reanalyze))
        self.experiment = {}
        for experiment_name in self.experiment_list:
            print(" " + experiment_name)
            self.experiment.update({experiment_name: 
                Experiment(self._file_handle[experiment_name], 
                           reanalyze=reanalyze)})


class Experiment:
    def __init__(self, experiment, reanalyze=False):
        self._experiment = experiment
        self.name = self._experiment.name
        self.protocol_list = self.GetProtocolList()
        self.PopulateProtocols(reanalyze=reanalyze)

    def GetProtocolList(self):
        return GetSubGroupList(self._experiment)
    
    def PopulateProtocols(self, reanalyze=False):
        print(" Populating Protocols, reanalyze= " + str(reanalyze))
        self.protocol = {}
        for protocol_name in self.protocol_list:
            print("  " + protocol_name)
            self.protocol.update({protocol_name:
                Protocol(self._experiment[protocol_name],
                         reanalyze=reanalyze)})


class Protocol:
    def __init__(self, protocol, reanalyze=False):
        self._protocol = protocol
        self.name = self._protocol.name
        self.speaker_out = protocol['Analog Out'].value[:,1]
        self.arena_out = protocol['Digital Out'].value[:,1]
        self.trial_list = self.GetCompletedTrials()
        self.n_samples = self._protocol.attrs['Number of Samples']
        self.PopulateTrials(reanalyze=reanalyze)
        self.AnalyzeProtocol(reanalyze=reanalyze)

    def GetCompletedTrials(self):
        trial_list = GetSubGroupList(self._protocol)
        for trial in trial_list:
            try :
                if not self._protocol[trial].attrs.get('Trial Completed'):
                    trial_list.remove(trial)
            except KeyError:
                trial_list.remove(trial)
        return trial_list

    def PopulateTrials(self, reanalyze=False):
        print("  Populating Trials, reanalyze= " + str(reanalyze))
        self.trial = {}
        for trial_name in self.trial_list:
            print("   " + trial_name)
            self.trial.update({trial_name:
                Trial(self._protocol[trial_name],
                      reanalyze=reanalyze)})
    
    def AnalyzeProtocol(self, reanalyze=False):
        if len(self.trial_list) == 0:
            return
        if 'Processed Data' in self._protocol:
            if reanalyze:
                del self._protocol['Processed Data']
            else:
                processed_data = self._protocol['Processed Data']
                return processed_data['Antennal Movement'],\
                       processed_data['Mean Antennal Movement'],\
                       self.arena_out,\
                       processed_data['Raster data'],\
                       processed_data['pre-GCFR']
        print("  Analyzing Protocol " + self.name)
        self._protocol.create_group('Processed Data')
        processed_data = self._protocol['Processed Data']
        antennal_movement = None
        spike_position_list_list = []
        for trial_name in self.trial_list:
            _, sp, am = self.trial[trial_name].AnalyzeTrial()
            if antennal_movement is None:
                antennal_movement = am
            else:
                antennal_movement = np.vstack((antennal_movement, am))
            spike_position_list_list.append(sp)
        spike_position_list_array = SpikePositionListListToArray(\
                                        spike_position_list_list)
        pre_GCFR = SpikePositionListListToPreGCFR(spike_position_list_list, 
                                                  len(self.arena_out)) 
        processed_data.create_dataset('Antennal Movement', 
                                      data=antennal_movement,
                                      fletcher32=True)
        if len(self.trial_list) == 1:
            processed_data.create_dataset('Mean Antennal Movement', 
                                          data=antennal_movement,
                                          fletcher32=True)
        else:
            processed_data.create_dataset('Mean Antennal Movement', 
                                          data=np.mean(antennal_movement, 
                                                       axis=0),
                                          fletcher32=True)
        processed_data.create_dataset('Raster data', 
                                      data=spike_position_list_array,
                                      fletcher32=True)                                    
        processed_data.create_dataset('pre-GCFR', 
                                      data=pre_GCFR,
                                      fletcher32=True)
        return processed_data['Antennal Movement'],\
               processed_data['Mean Antennal Movement'],\
               self.arena_out,\
               processed_data['Raster data'],\
               processed_data['pre-GCFR']

class Trial:
    def __init__(self, trial, reanalyze=False):
        self._trial = trial
        self.name = self._trial.name
        self.AnalyzeTrial(reanalyze=reanalyze)
        
    def AnalyzeTrial(self, reanalyze=False):
        if 'Processed Data' in self._trial:
            if reanalyze:
                del self._trial['Processed Data']
            else:
                return self._trial['Processed Data']['Membrane Potential'],\
                       self._trial['Processed Data']['Spike Position List'],\
                       self._trial['Processed Data']['Antennal Movement']
        print("    Analyzing trial " + self.name)
        self._trial.create_group('Processed Data')
        trial_analog_in = self._trial['Analog In'].value
        membrane_potential = trial_analog_in[:,0]
        antennal_movement = hallEffectSensorToDisplacement(trial_analog_in[:,2])
        membrane_potential = Filter(membrane_potential, 50, 
                                    f_pass='highpass', poles=3)
        membrane_potential = membrane_potential - membrane_potential[0]
        antennal_movement = Filter(antennal_movement, 500)
        antennal_movement = antennal_movement - \
                            np.mean(antennal_movement[:5000])
        spike_position_list = GetSpikePositionList(membrane_potential)
        processed_data = self._trial['Processed Data']
        if "Membrane Potential" in processed_data:
            processed_data["Membrane Potential"][:] = membrane_potential
        else:
            processed_data.create_dataset("Membrane Potential", 
                                          data=membrane_potential, 
                                          fletcher32=True)
        if "Antennal_Movement" in processed_data:
            processed_data["Antennal Movement"][:] = antennal_movement
        else:
            processed_data.create_dataset("Antennal Movement", 
                                          data=antennal_movement, 
                                          fletcher32=True)
        if "Spike Position List" in processed_data:
            del processed_data["Spike Position List"]
        processed_data.create_dataset("Spike Position List", 
                                      data=spike_position_list, 
                                      fletcher32=True)
        self._trial.file.flush()
        return membrane_potential, spike_position_list, antennal_movement
