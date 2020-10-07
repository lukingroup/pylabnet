import pyqtgraph as pg
import numpy as np
import copy

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogClient, LogHandler


class Dataset:

    def __init__(self, gui:Window, log:LogClient=None, data=None, 
        x=None, graph=None):
        """ Instantiates an empty generic dataset 
        
        :param gui: (Window) GUI window for data graphing
        :param log: (LogClient)
        :param data: initial data to set
        :param x: x axis
        :param graph: (pg.PlotWidget) graph to use
        """

        self.log = LogHandler(log)
        self.metadata = self.log.get_metadata()

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
            graph=graph
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
        else:
            self.graph = graph
        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                len(self.graph.getPlotItem().curves)
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


class AveragedHistogram(Dataset):
    """ Subclass for plotting averaged histogram """

    def __init__(self, gui:Window, log:LogClient=None, data=None, 
        x=None, graph=None):
        """ Instantiates an empty generic dataset 
        
        :param gui: (Window) GUI window for data graphing
        :param log: (LogClient)
        :param data: initial data to set
        :param x: x axis
        :param graph: (pg.PlotWidget) graph to use
        """

        self.recent_data = None
        self.preselection = True
        super().__init__(gui, log, data, x, graph)

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


# Useful mappings

def moving_average(dataset, prev_dataset=None):
	n=20
	ret = np.cumsum(dataset.data)
	ret[n:] = ret[n:] - ret[:-n]
	prev_dataset.set_data(data=ret[n-1:]/n)