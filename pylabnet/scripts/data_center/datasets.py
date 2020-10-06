import pyqtgraph as pg

from pylabnet.gui.pyqt.external_gui import Window


class Dataset:

    def __init__(self, gui: Window, data=None, x=None):
        """ Instantiates an empty generic dataset 
        
        :param gui: (Window) GUI window for data graphing
        :param data: initial data to set
        :param x: x axis
        """

        # Set data registers
        self.data = data
        self.x = x

        # Configure data visualization
        self.gui = gui
        self.visualize()

    def process(self, name, mapping=None):
        """ Processes data to produce a new processed dataset
        
        :param name: (str) name of processed dataset
            becomes a Dataset object (or child) as attribute of self
        :param mapping: (function) function which transforms Dataset to processed Dataset
        """

        # If there is no mapping we just make a copy of the data
        # if mapping is None:
        #     setattr(self, name, Dataset(gui, self.data, self.x))

        # # Otherwise we apply the process
        # else:
        #     setattr(self, name, mapping(self))
        pass

    def set_data(self, data=None, x=None):
        """ Sets data

        :param data: data to set
        :param x: x axis
        """

        self.data = data

        if x is not None:
            self.x = x

    def visualize(self):
        """ Prepare data visualization on GUI """

        self.graph = self.gui.add_graph()
        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[0])
        )
        self.update()

    def update(self):
        """ Updates current data to plot"""

        if self.data is not None:
            if self.x is not None:
                self.curve.setData(self.x, self.data)
            else:
                self.curve.setData(self.data)
