# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""
import numpy as np
import scipy.signal
import math
import time
import re
import thread
import Queue
import h5py
import tempfile
import random
import os
import signal
import zipfile
from msvcrt import getch
from itertools import product

arena_brightness_percent = 2

outputQ = Queue.Queue(maxsize=50)
inputQ = Queue.Queue()
experimentEnd = None
experimentAbort = None

sampling_rate = 10000
sample_section = 1000

class outputItem:
    def __init__(self):
        self.analog_out = None
        self.digital_out = None
        self.new_protocol = None
        self.arena_angular_size = None
        self.arena_mode = None
        self.protocol_name = None
        self.read_till = None

class inputItem:
    def __init__(self):
        self.analog_in = None
        self.digital_in = None

def dataArray(shape=(1000,2), digital=False):
    if digital:
        data_type = np.uint8
    else:
        data_type = np.float64
    return np.zeros(shape, dtype=data_type)

def secondsToHMS(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

def saveSelf(destination):
    zip_file = zipfile.ZipFile(destination, 'w')
    for root, dirs, files in os.walk(os.path.dirname(__file__)):
        for file_name in files:
            if file_name[-3:] in ['pyc', 'df5', 'swp', 'ini', 'wpr', 'wpu'] or \
               file_name[0] == '.':
                continue
            zip_file.write(os.path.join(root, file_name))
        if '.git' in dirs:
            dirs.remove('.git')        
    zip_file.close()

def prepareDirectoryForExperiment(data_file_path):
    dir_of_data_file = os.path.realpath(os.path.dirname(data_file_path))
    if not os.path.exists(dir_of_data_file):
        os.makedirs(dir_of_data_file)
    if not os.path.isfile(os.path.join(dir_of_data_file, 'ExperimentControl.zip')):
        saveSelf(os.path.join(dir_of_data_file, 'ExperimentControl.zip'))


def product2(args):
    return product(*args)

def expandStimulusRepresentation(compactStimulusRepresentation):
    a = "".join(compactStimulusRepresentation.split("\n"))
    a = "".join(a.split(" "))
    b = a.split(";")
    x=[]
    for c in b:
        m=re.split(r"\[(.*?)\]",c)
        n=[]
        for i in m:
            n.append(i.split("/"))
        t = product2(n)
        t2 = []
        for o in t:
            t2.append("".join(o))
        t = ";".join(t2)
        if t != "":
            x.append(t)
    return ";".join(x)

#full stimulus
'''
vis(4,5,4,10,[0/1/2/3],40);
vis(4,8,4,10,[4/5],40);
vic(4,5,4,10,[0/1/2/3],[0,100/100,0]);
mep(4,[0.02,4.08/0.1,4/0.5,4],0.4);
men(4,5,4,120,0.4);
mec(4,5,4,[0,120/120,0],0.4);
mcv(4,5,5,0,4,[0,120/120,0],0.4,10,[0/1/2/3],40);
mcv(4,8,8,0,4,[0,120/120,0],0.4,10,[4/5],40);
'''