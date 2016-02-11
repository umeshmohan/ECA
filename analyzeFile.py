#!/usr/bin/env python
from ExperimentControlandAnalysis.dataFileHandling import NeuronData

import sys
data_file = NeuronData(sys.argv[1])
data_file.close()
