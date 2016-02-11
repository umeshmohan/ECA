#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""

import pyqtgraph as pg
from ExperimentControlandAnalysis.plotting import ExploreDataFile

pg.mkQApp()
explore_data_file_gui = ExploreDataFile()
explore_data_file_gui.show()

if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        pg.QtGui.QApplication.instance().exec_()
