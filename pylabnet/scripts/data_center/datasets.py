import pyqtgraph as pg
import numpy as np
import copy
from PyQt5 import QtWidgets, QtCore

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogClient, LogHandler


class Dataset:

    def __init__(self, gui:Window, log:LogClient=None, data=None, 
        x=None, graph=None, name=None, **kwargs):
        """ Instantiates an empty generic dataset 
        
        :param gui: (Window) GUI window for data graphing
        :param log: (LogClient)
        :param data: initial data to set
        :param x: x axis
        :param graph: (pg.PlotWidget) graph to use
        """

        self.log = LogHandler(log)
        self.metadata = self.log.get_metadata()
        if name is None:
            self.name = self.__class__.__name__
        else:
            self.name = name

        # Set data registers
        self.data = data
        self.x = x
        self.children = {}
        self.mapping = {}

        # Configure data visualization
        self.gui = gui
        self.visualize(graph)

    def add_child(self, name, mapping=None, new_plot=True):
        """ Adds a child dataset with a particular data mapping
        
        :param name: (str) name of processed dataset
            becomes a Dataset object (or child) as attribute of self
        :param mapping: (function) function which transforms Dataset to processed Dataset
        :param new_plot: (bool) whether or not to use a new plot
        """

        if new_plot:
            graph = None
        else:
            graph = self.graph

        self.children[name] = self.__class__(
            gui=self.gui, 
            data=self.data,
            graph=graph,
            name=name
        )

        if mapping is not None:
            self.mapping[name] = mapping
    
    def set_data(self, data=None, x=None):
        """ Sets data

        :param data: data to set
        :param x: x axis
        """

        self.data = data

        if x is not None:
            self.x = x

    def visualize(self, graph):
        """ Prepare data visualization on GUI 
        
        :param graph: (pg.PlotWidget) graph to use
        """

        if graph is None:
            self.graph = self.gui.add_graph()
            self.graph.getPlotItem().setTitle(self.name)
        else:
            self.graph = graph
        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                self.gui.graph_layout.count()-1
            ])
        )
        self.update()

    def update(self):
        """ Updates current data to plot"""

        if self.data is not None:
            if self.x is not None:
                self.curve.setData(self.x, self.data)
            else:
                self.curve.setData(self.data)

        for name, child in self.children.items():
            # If we need to process the child data, do it
            if name in self.mapping:
                self.mapping[name](self, prev_dataset=child)
            child.update()

    def interpret_status(self, status):
        """ Interprets a status flag for exepriment monitoring
        
        :param status: (str) current status message
        """

        if status == 'OK':
            self.gui.presel_status.setText(status)
            self.gui.presel_status.setStyleSheet('')
        elif status == 'BAD':
            self.gui.presel_status.setText(status)
            self.gui.presel_status.setStyleSheet('background-color: red;')
        else:
            self.gui.presel_status.setText(status)
            self.gui.presel_status.setStyleSheet('background-color: gray;')


class AveragedHistogram(Dataset):
    """ Subclass for plotting averaged histogram """

    def __init__(self, *args, **kwargs):
        """ Instantiates an empty generic dataset 
        
        :param gui: (Window) GUI window for data graphing
        :param log: (LogClient)
        :param data: initial data to set
        :param x: x axis
        :param graph: (pg.PlotWidget) graph to use
        :param name: (str) name of dataset
        """

        self.recent_data = None
        self.preselection = True
        super().__init__(*args, **kwargs)

    def set_data(self, data=None, x=None):
        """ Sets data by adding to previous histogram

        :param data: new data to set
        :param x: x axis
        """

        # Cast as a numpy array if needed
        if isinstance(data, list):
            self.recent_data = np.array(data)
        else:
            self.recent_data = data

        if self.data is None:
            self.data = copy.deepcopy(self.recent_data)
        else:
            self.data += self.recent_data

        for name, child in self.children.items():
            # If we need to process the child data, do it
            if name in self.mapping:
                self.mapping[name](self, prev_dataset=child)

    def update(self):
        """ Updates current data to plot"""

        if self.data is not None:
            if self.x is not None:
                self.curve.setData(self.x, self.data)
            else:
                self.curve.setData(self.data)

        for child in self.children.values():
            child.update()


class PreselectedHistogram(AveragedHistogram):
    """ Measurement class for showing raw averaged, single trace,
        and preselected data """

    def __init__(self, *args, **kwargs):
        """ Instantiates preselected histogram measurement 
        
        see parent classes for details
        """

        super().__init__(*args, **kwargs)
        self.add_child(name='Single Trace', mapping=self.recent)
        self.presel_params = None
        self.setup_preselection(threshold=int)

    def setup_preselection(self, **kwargs):
        
        self.popup = PreselectionPopup(**kwargs)
        self.popup.parameters.connect(self.fill_parameters)
    
    def fill_parameters(self, params):

        self.presel_params = params
        self.add_child(name='Preselected Trace', mapping=self.preselect)
    
    def preselect(self, dataset, prev_dataset):
        """ Preselects based on user input parameters """

        if np.sum(dataset.recent_data) > self.presel_params['threshold']:
            dataset.preselection = False
        else:
            dataset.preselection = True
        
        if dataset.preselection:

            if prev_dataset.data is None:
                prev_dataset.data = dataset.recent_data
            else:
                prev_dataset.data += dataset.recent_data
    
    def add_child(self, name, mapping=None, new_plot=True):
        """ Adds a child dataset with a particular data mapping
        
        :param name: (str) name of processed dataset
            becomes a Dataset object (or child) as attribute of self
        :param mapping: (function) function which transforms Dataset to processed Dataset
        :param new_plot: (bool) whether or not to use a new plot
        """

        if new_plot:
            graph = None
        else:
            graph = self.graph

        self.children[name] = AveragedHistogram(
            gui=self.gui, 
            data=self.data,
            graph=graph,
            name=name
        )

        if mapping is not None:
            self.mapping[name] = mapping
    
    @staticmethod
    def recent(dataset, prev_dataset):
	    prev_dataset.data = dataset.recent_data


class PreselectionPopup(QtWidgets.QWidget):
    """ Widget class of Add preselection popup"""
    parameters = QtCore.pyqtSignal(dict)

    def __init__(self, **presel_params):
        """ Instantiates window

        :param presel_params: (dict) with keys giving parameter
            name and value giving parameter type
        """

        QtWidgets.QWidget.__init__(self)

        # Create layout
        self.base_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.base_layout)
        self.params = {}

        # Add labels and widgets to layout
        for param_name, param_type in presel_params.items():
            layout = QtWidgets.QHBoxLayout()
            layout.addWidget(QtWidgets.QLabel(param_name))
            if param_type is int:
                self.params[param_name] = QtWidgets.QSpinBox()
            elif param_type is float:
                self.params[param_name] = QtWidgets.QDoubleSpinBox()
            else:
                self.params[param_name] = QtWidgets.QLabel()
            layout.addWidget(self.params[param_name])
            self.base_layout.addLayout(layout)

        # Add button to configure
        self.configure_button = QtWidgets.QPushButton(text='Configure Preselection')
        self.base_layout.addWidget(self.configure_button)
        self.configure_button.clicked.connect(self.return_params)
        self.show()

    def return_params(self):
        """ Returns all parameter values and closes """

        ret = {}
        for param_name, widget in self.params.items():
            try:
                ret[param_name] = widget.value()
            except AttributeError:
                ret[param_name] = widget.text()
        self.parameters.emit(ret)
        self.close()


# Useful mappings

def moving_average(dataset, prev_dataset=None):
	n=20
	ret = np.cumsum(dataset.data)
	ret[n:] = ret[n:] - ret[:-n]
	prev_dataset.set_data(data=ret[n-1:]/n)