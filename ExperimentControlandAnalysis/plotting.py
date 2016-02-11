# -*- coding: utf-8 -*-
"""
@author: Umesh Mohan (umeshm@ncbs.res.in)
"""

from .common import np
from .dataFileHandling import NeuronData, Experiment, Protocol, Trial
from .analysis import GCFR

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.exporters as pgExporters
from os import unlink
#import pyx

getOpenFileName = QtGui.QFileDialog.getOpenFileName
getSaveFileName = QtGui.QFileDialog.getSaveFileName

class SpikesItem(pg.GraphicsObject):
    def __init__(self, t, spike_position_list, 
                 start_point, end_point, color='r'):
        pg.GraphicsObject.__init__(self)
        self.t = t
        self.spike_position_list = spike_position_list
        if start_point > end_point:
            start_point, end_point = end_point, start_point
        self.start_point = start_point
        self.end_point = end_point
        self.color = color
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.color))
        for spike in self.spike_position_list:
            if spike != -1:
                p.drawLine(QtCore.QPointF(self.t[spike], self.start_point), 
                           QtCore.QPointF(self.t[spike], self.end_point))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())


def PlotTrial(trial_name, membrane_potential, spike_position_list, 
              antennal_movement, arena_out,
              colors={'mp':'w', 'sp':'y', 'am':'r', 'ls':'g'},
              win=None):
    if win is None:
        win = pg.GraphicsWindow(trial_name)
    t = np.linspace(0, len(arena_out)/10000.0, 
                    num=len(arena_out), endpoint=False)
    plt_mp = win.addPlot(name="plot_mp", title="Membrane Potential", 
                       row=0, col=0)
    plt_am = win.addPlot(name="plot_am", title="Antennal Movement", 
                       row=1, col=0)
    plt_ls = win.addPlot(name="plot_ls", title="LED arena step", 
                       row=2, col=0) 
    spike_plot_item = SpikesItem(t, spike_position_list, 
                                 np.min(membrane_potential), 
                                 np.max(membrane_potential), 
                                 color=colors['sp'])
    plt_mp.addItem(spike_plot_item)
    plt_mp.plot(t, membrane_potential, pen=colors['mp'])
    plt_am.plot(t, antennal_movement, pen=colors['am'])
    plt_ls.plot(t, arena_out, pen=colors['ls'])    
    plt_am.setXLink(plt_mp)
    plt_ls.setXLink(plt_mp)
    return win


def PlotProtocol(protocol_name, antennal_movement_list, mean_antennal_movement, 
                 arena_out, spike_position_list_array, GCFR,
                 colors={'am': (50,0,0), 'amm':'r', 'ls':'g',
                         'sp':'w', 'gcfr':'y'},
                 win=None):
    if win is None:
        win = pg.GraphicsWindow(protocol_name)
    t = np.linspace(0, len(arena_out)/10000.0, 
                    num=len(arena_out), endpoint=False)
    plt_am = win.addPlot(name="plot_am", title="Antennal Movement", 
                         row=0, col=0)
    plt_ls = win.addPlot(name="plot_ls", title="LED arena step", 
                         row=1, col=0) 
    plt_raster = win.addPlot(name="plot_raster", title="Raster", 
                             row=2, col=0) 
    plt_gcfr = win.addPlot(name="plot_gcfr", title="GCFR", 
                           row=3, col=0)                              
    for antennal_movement in antennal_movement_list:
        plt_am.plot(t, antennal_movement, pen=colors['am'])
    plt_am.plot(t, mean_antennal_movement, pen=colors['amm'])
    plt_ls.plot(t, arena_out, pen=colors['ls'])
    trial = 1
    for spike_position_list in spike_position_list_array:
        spike_plot_item = SpikesItem(t, spike_position_list, 
                                     trial - 0.45, trial + 0.45, 
                                     color=colors['sp'])
        plt_raster.addItem(spike_plot_item)
        trial += 1
    plt_gcfr.plot(t, GCFR, pen=colors['gcfr'])
    plt_ls.setXLink(plt_am)
    plt_raster.setXLink(plt_am)
    plt_gcfr.setXLink(plt_am)
    return win

    
class ExploreDataFile(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.neuron_data = None
        self.setWindowTitle("Experiment Control - Data Analysis & Visualization")
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter2 = QtGui.QSplitter()
        self.splitter2.setOrientation(QtCore.Qt.Vertical)
        self.layout.addWidget(self.splitter)
        self.splitter.addWidget(self.splitter2)
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.tree = ParameterTree(showHeader=False)
        self.params = Parameter.create(name='params', type='group', 
                                       children=[dict(name='Reanalyze', 
                                                      type='bool', 
                                                      value=False),
                                                 dict(name='Load', 
                                                      type='action'),
                                                 dict(name='GCFR-sigma (ms)', 
                                                      type='float',
                                                      value=100.0, step=0.1, 
                                                      limits=[1, 5000]),
                                                 dict(name='Save', 
                                                      type='action'),
                                                 ])
        self.tree.setParameters(self.params, showTop=False)
        #self.params.param('Save').sigActivated.connect(self.SavePlot)
        self.params.param('Load').sigActivated.connect(self.OpenDataFile)
        self.splitter2.addWidget(self.tree)
        self.trial_list_tree = pg.TreeWidget(parent=self.splitter2)
        self.splitter.addWidget(self.plot_widget)
        self.trial_list_tree.setColumnCount(1)
    
    def OpenDataFile(self):
        print("Reanalyze= " + str(self.params['Reanalyze']))
        file_name = str(getOpenFileName(self, 
                                        "Neuron Data", "",
                                        "HDF5 Files (*.hdf5 *.h5)"))
        if file_name == '':
            return
        self.LoadData(file_name, reanalyze=self.params['Reanalyze'])
        self.setWindowTitle("Experiment Control - Data Analysis & Visualization: " + file_name)

    def LoadData(self, neuron_data_file_name, reanalyze=False):
        if self.neuron_data is not None:
            self.neuron_data.close()
        self.neuron_data = NeuronData(neuron_data_file_name, 
                                      reanalyze=reanalyze)
        self.trial_list_tree.clear()
        for experiment_name in self.neuron_data.experiment_list:
            experiment_tree_item = QtGui.QTreeWidgetItem([experiment_name])
            self.trial_list_tree.addTopLevelItem(experiment_tree_item)
            experiment = self.neuron_data.experiment[experiment_name]
            if len(experiment.protocol_list) > 0:
                for protocol_name in experiment.protocol_list:
                    protocol_tree_item = QtGui.QTreeWidgetItem([protocol_name])
                    experiment_tree_item.addChild(protocol_tree_item)
                    protocol = experiment.protocol[protocol_name]
                    if len(protocol.trial_list) > 0:
                        for trial_name in protocol.trial_list:
                            trial_tree_item = QtGui.QTreeWidgetItem([trial_name])
                            protocol_tree_item.addChild(trial_tree_item)
                    else:
                        self.trial_list_tree.removeItemWidget(protocol_tree_item, 0)
            else:
                self.trial_list_tree.removeItemWidget(experiment_tree_item, 0)
        self.trial_list_tree.itemClicked.connect(self.UpdatePlot)

    def SavePlotData(self):
        file_name = str(getSaveFileName(self, 
                                        "Save Plot data", "",
                                        "CSV (*.csv)"))
        if file_name == '':
            return
        x_range = self.plot_widget.getItem(0,0).viewRange()[0]
        t = np.linspace(0, len(arena_out)/10000.0, 
                    num=len(arena_out), endpoint=False)
        '''if self.data['type'] == "trial":
            c = pyx.canvas.canvas()
        if self.data['type'] == "protocol":
            c = pyx.canvas.canvas()'''
        
    
    def UpdatePlot(self, item, column):
        if str(item.text(0)) in self.neuron_data.experiment_list:
            return
        self.plot_widget.clear()
        if item.childCount() == 0:
            trial_name = str(item.text(0))
            protocol_name = str(item.parent().text(0))
            experiment_name = str(item.parent().parent().text(0))
            protocol = self.neuron_data.experiment[experiment_name].protocol[protocol_name]
            membrane_potential, spike_position_list, antennal_movement = \
                protocol.trial[trial_name].AnalyzeTrial()
            self.data = {'type': "trial",
                         'trial name': trial_name,
                         'membrane potential': membrane_potential,
                         'spike position list': spike_position_list,
                         'antennal movement': antennal_movement,
                         'arena out': protocol.arena_out}
            PlotTrial(trial_name, membrane_potential, spike_position_list, 
                      antennal_movement, protocol.arena_out, 
                      win=self.plot_widget)
        else:
            protocol_name = str(item.text(0))
            experiment_name = str(item.parent().text(0))
            protocol = self.neuron_data.experiment[experiment_name].protocol[protocol_name]
            antennal_movement_list, mean_antennal_movement, arena_out, \
                raster_data, pre_GCFR = protocol.AnalyzeProtocol()
            gcfr = GCFR(pre_GCFR, self.params['GCFR-sigma (ms)'])
            self.data = {'type': "protocol",
                         'protocol name': protocol_name,
                         'antennal movement list': antennal_movement_list, 
                         'mean antennal movement': mean_antennal_movement, 
                         'arena out': arena_out, 
                         'raster data': raster_data, 
                         'GCFR': gcfr} 
            PlotProtocol(protocol_name, antennal_movement_list, 
                         mean_antennal_movement, arena_out, raster_data, 
                         gcfr, win=self.plot_widget)
"""
def PlotTrial(trial_name, membrane_potential, spike_position_list, 
    antennal_movement, arena_out,
    colors={'mp':'w', 'sp':'y', 'am':'r', 'ls':'g'},
    win=None):
def PlotProtocol(protocol_name, antennal_movement_list, mean_antennal_movement, 
    arena_out, spike_position_list_array, GCFR,
    colors={'am': (50,0,0), 'amm':'r', 'ls':'g',
    'sp':'w', 'gcfr':'y'},
    win=None):
def AnalyzeProtocol(self, reanalyze=False):
    return processed_data['Antennal Movement'],\
           processed_data['Mean Antennal Movement'],\
           self.arena_out,\
           processed_data['Raster data'],\
           processed_data['pre-GCFR']
"""
