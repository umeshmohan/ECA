# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""
from ExperimentControlandAnalysis import runExperiment
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("data_file")
parser.add_argument("experiment")
parser.add_argument("-c", "--mCalib_file", type=str, default="None")
parser.add_argument("-p", "--mCalib_protocol", type=str, default="mCalib")    
parser.add_argument("-r", "--repeats", type=int, default=10)
args = parser.parse_args()

experiment = args.experiment
if args.mCalib_file == "None":
    mCalib = False
else:
    mCalib = {"file": args.mCalib_file,
              "protocol": args.mCalib_protocol}
repeats = args.repeats
data_file_name = args.data_file
file_mode = 'a'
runExperiment.runExperiment(data_file_name, file_mode=file_mode, experiment=experiment, 
              mCalib=mCalib, repeats=repeats)
              
              
# vim: set ts=4 sw=4 ft=python ai nu et