import pyqtgraph as pg
import numpy as np
import copy
import time
from PyQt5 import QtWidgets, QtCore

from pylabnet.gui.pyqt.external_gui import Window, ParameterPopup
from pylabnet.utils.logging.logger import LogClient, LogHandler
from pylabnet.utils.helper_methods import save_metadata, generic_save, pyqtgraph_save, fill_2dlist


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
        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}
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
        self.widgets = {}

        # Configure data visualization
        self.gui = gui
        self.visualize(graph, **kwargs)

    def add_child(self, name, mapping=None, data_type=None,
        new_plot=True, **kwargs):
        """ Adds a child dataset with a particular data mapping

        :param name: (str) name of processed dataset
            becomes a Dataset object (or child) as attribute of self
        :param mapping: (function) function which transforms Dataset to processed Dataset
        :param data_type: (Class) type of Dataset to add
        :param new_plot: (bool) whether or not to use a new plot
        """

        if new_plot:
            graph = None
        else:
            graph = self.graph

        if data_type is None:
            data_type = self.__class__

        self.children[name] = data_type(
            gui=self.gui,
            data=self.data,
            graph=graph,
            name=name,
            **kwargs
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

        self.set_children_data()

    def set_children_data(self):
        """ Sets all children data with mappings """

        for name, child in self.children.items():
            # If we need to process the child data, do it
            if name in self.mapping:
                self.mapping[name](self, prev_dataset=child)
    
    def visualize(self, graph, **kwargs):
        """ Prepare data visualization on GUI

        :param graph: (pg.PlotWidget) graph to use
        """

        if graph is None:
            self.graph = self.gui.add_graph()
            self.graph.getPlotItem().setTitle(self.name)
        else:
            self.graph = graph

        if 'color_index' in kwargs:
            color_index = kwargs['color_index']
        else:
            color_index = self.gui.graph_layout.count()-1
        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                color_index
            ])
        )
        self.update(**kwargs)

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None:
            if self.x is not None:
                self.curve.setData(self.x[:len(self.data)], self.data)
            else:
                self.curve.setData(self.data)

        for child in self.children.values():
            child.update(**kwargs)

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

    def save(self, filename=None, directory=None, date_dir=True):

        generic_save(
            data=self.data,
            filename=f'{filename}_{self.name}',
            directory=directory,
            date_dir=date_dir
        )
        if self.x is not None:
            generic_save(
                data=self.x,
                filename=f'{filename}_{self.name}_x',
                directory=directory,
                date_dir=date_dir
            )

        if hasattr(self, 'graph'):
            pyqtgraph_save(
                self.graph.getPlotItem(),
                f'{filename}_{self.name}',
                directory,
                date_dir
            )

        for child in self.children.values():
            child.save(filename, directory, date_dir)

        save_metadata(self.log, filename, directory, date_dir)

    def add_params_to_gui(self, **params):
        """ Adds parameters of dataset to gui 
        
        :params: (dict) containing all parameter names and values
        """

        for name, value in params.items():

            hbox = QtWidgets.QHBoxLayout()
            hbox.addWidget(QtWidgets.QLabel(name))
            if type(value) is int:
                self.widgets[name] = QtWidgets.QSpinBox()
                self.widgets[name].setMaximum(1000000000)
                self.widgets[name].setMinimum(-1000000000)
                self.widgets[name].setValue(value)
            elif type(value) is float:
                self.widgets[name] = QtWidgets.QDoubleSpinBox()
                self.widgets[name].setMaximum(1000000000.)
                self.widgets[name].setMinimum(-1000000000.)
                self.widgets[name].setDecimals(6)
                self.widgets[name].setValue(value)
            else:
                self.widgets[name] = QtWidgets.QLabel(str(value))

            hbox.addWidget(self.widgets[name])
            self.gui.dataset_layout.addLayout(hbox)


class AveragedHistogram(Dataset):
    """ Subclass for plotting averaged histogram """

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

        self.set_children_data()


class PreselectedHistogram(AveragedHistogram):
    """ Measurement class for showing raw averaged, single trace,
        and preselected data using a gated counter for preselection"""

    def __init__(self, *args, **kwargs):
        """ Instantiates preselected histogram measurement

        see parent classes for details
        """

        kwargs['name'] = 'Average Histogram'
        self.preselection = True
        super().__init__(*args, **kwargs)
        self.add_child(name='Single Trace', mapping=self.recent, data_type=Dataset)
        if 'presel_params' in self.config:
            self.presel_params = self.config['presel_params']
            self.fill_parameters(self.presel_params)
        else:
            self.presel_params = None
            self.setup_preselection(threshold=float)
        if 'presel_data_length' in self.config:
            presel_data_length = self.config['presel_data_length']
        else:
            presel_data_length = None
        self.add_child(
            name='Preselection Counts',
            data_type=InfiniteRollingLine,
            data_length=presel_data_length
        )

    def setup_preselection(self, **kwargs):

        self.popup = ParameterPopup(**kwargs)
        self.popup.parameters.connect(self.fill_parameters)

    def fill_parameters(self, params):

        self.presel_params = params
        self.add_child(
            name='Preselected Trace',
            mapping=self.preselect,
            data_type=AveragedHistogram
        )
        self.log.update_metadata(presel_params = self.presel_params)

    def preselect(self, dataset, prev_dataset):
        """ Preselects based on user input parameters """

        if dataset.children['Preselection Counts'].data[-1] < self.presel_params['threshold']:
            dataset.preselection = True
            if prev_dataset.data is None:
                prev_dataset.data = dataset.recent_data
            else:
                prev_dataset.data += dataset.recent_data
        else:
            dataset.preselection = False

    def set_data(self, data=None, x=None, preselection_data=None):
        """ Sets the data for a new round of acquisition

        :param data: histogram data from latest acquisition
            note the histogram should have been cleared prior to acquisition
        :param x: x axis for data
        :param preselection_data: (float) value of preselection indicator
            from latest acquisition
        """

        self.children['Preselection Counts'].set_data(preselection_data)
        super().set_data(data, x)

    def interpret_status(self, status):
        super().interpret_status(status)

        for name, child in self.children.items():
            if name in self.mapping and self.mapping[name] == self.preselect:
                vb = child.graph.getPlotItem().getViewBox()
                if status == 'BAD':
                    vb.setBackgroundColor(0.1)
                else:
                    vb.setBackgroundColor(0.0)

    @staticmethod
    def recent(dataset, prev_dataset):
	    prev_dataset.data = dataset.recent_data


class InvisibleData(Dataset):
    """ Dataset which does not plot """

    def visualize(self, graph, **kwargs):
        self.curve = pg.PlotDataItem()


class RollingLine(Dataset):
    """ Implements a rolling dataset where new values are
        added incrementally e.g. in time-traces """

    def __init__(self, *args, **kwargs):

        # We need to know the data length, so prompt if necessary
        if 'data_length' in kwargs and kwargs['data_length'] is not None:
            self.data_length = kwargs['data_length']
        else:
            self.popup = ParameterPopup(data_length=int)
            self.waiting = True
            self.popup.parameters.connect(self.setup_axis)
        super().__init__(*args, **kwargs)

    def setup_axis(self, params):

        self.data_length = params['data_length']
        self.waiting = False

    def set_data(self, data):
        """ Updates data

        :param data: (scalar) data to add
        """

        if self.data is None:
            self.data = np.array([data])

        else:
            if len(self.data) == self.data_length:
                self.data = np.append(self.data, data)[1:]
            else:
                self.data = np.append(self.data, data)

        for name, child in self.children.items():
            # If we need to process the child data, do it
            if name in self.mapping:
                self.mapping[name](self, prev_dataset=child)


class InfiniteRollingLine(RollingLine):
    """ Extension of RollingLine that stores the data
        indefinitely, but still only plots a finite amount """

    def set_data(self, data):
        """ Updates data

        :param data: (scalar) data to add
        """

        if self.data is None:
            self.data = np.array([data])

        else:
            self.data = np.append(self.data, data)

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None:

            if len(self.data) > self.data_length:
                if self.x is not None:
                    self.curve.setData(self.x, self.data[-self.data_length:])
                else:
                    self.curve.setData(self.data[-self.data_length:])

                for name, child in self.children.items():
                    # If we need to process the child data, do it
                    if name in self.mapping:
                        self.mapping[name](self, prev_dataset=child)
                    child.update(**kwargs)
            else:
                super().update(**kwargs)


class TriangleScan1D(Dataset):
    """ 1D Triangle sweep of a parameter """

    def __init__(self, *args, **kwargs):

        self.args = args
        self.kwargs = kwargs
        self.all_data = None
        self.update_hmap = False
        self.stop = False
        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}
        self.config.update(kwargs)

        # # First, try to get scan parameters from GUI
        # if hasattr(self, 'widgets'):
        #     if set(['min', 'max', 'pts', 'reps']).issubset(self.widgets.keys()):
        #         self.widgets['reps'].setValue(0)
        #         self.fill_params(dict(
        #             min = self.widgets['min'].value(),
        #             max = self.widgets['max'].value(),
        #             pts = self.widgets['pts'].value()
        #         ))

        # Get scan parameters from config
        if set(['min', 'max', 'pts']).issubset(self.kwargs.keys()):
            self.fill_params(self.kwargs)

        # Prompt user if not provided in config
        else:
            self.popup = ParameterPopup(min=float, max=float, pts=int)
            self.popup.parameters.connect(self.fill_params)
    
    def fill_params(self, config):
        """ Fills the min max and pts parameters """

        self.min, self.max, self.pts = config['min'], config['max'], config['pts']
        
        if 'backward' in self.kwargs:
            self.backward = True
            self.kwargs.update(dict(
                x=np.linspace(self.max, self.min, self.pts),
                name='Bwd trace'
            ))
        else:
            self.backward = False
            self.kwargs.update(dict(
                x=np.linspace(self.min, self.max, self.pts),
                name='Fwd trace'
            ))
        super().__init__(*self.args, **self.kwargs)

        # Add child for averaged plot
        self.add_child(
            name=f'{"Bwd" if self.backward else "Fwd"} avg',
            mapping=self.avg,
            data_type=Dataset,
            new_plot=False,
            x=self.x,
            color_index=2
        )

        # Add child for HMAP
        self.add_child(
            name=f'{"Bwd" if self.backward else "Fwd"} scans',
            mapping=self.hmap,
            data_type=HeatMap,
            min=self.min,
            max=self.max,
            pts=self.pts
        )

        # Add child for backward plot
        if not self.backward:
            self.add_child(
                name='Bwd trace',
                min=self.min,
                max=self.max,
                pts=self.pts,
                backward=True,
                color_index=1
            )

            for i in reversed(range(self.gui.dataset_layout.count())): 
                self.gui.dataset_layout.itemAt(i).setParent(None)
            self.add_params_to_gui(
                min=config['min'],
                max=config['max'],
                pts=config['pts'],
                reps=0
            )

    def avg(self, dataset, prev_dataset):
        """ Computes average dataset (mapping) """

        # If we have already integrated a full dataset, avg
        if dataset.reps > 1:
            current_index = len(dataset.data) - 1
            prev_dataset.data[current_index] = (
                prev_dataset.data[current_index]*(dataset.reps-1)
                + dataset.data[-1]
            )/(dataset.reps)
        else:
            prev_dataset.data = dataset.data

    def set_data(self, value):

        if self.data is None:
            self.reps = 1
            self.data = np.array([value])
        else:
            self.data = np.append(self.data, value)

        if len(self.data) > self.pts:
            self.update_hmap = True
            self.reps += 1

            try:
                reps_to_do = self.widgets['reps'].value()
                if reps_to_do > 0 and self.reps > reps_to_do:
                    self.stop = True
            except KeyError:
                pass

            if self.all_data is None:
                self.all_data = self.data[:-1]
            else:
                self.all_data = np.vstack((self.all_data, self.data[:-1]))
            self.data = np.array([self.data[-1]])

        self.set_children_data()

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None and len(self.data) <= len(self.x):  
            self.curve.setData(self.x[:len(self.data)], self.data)
        
        for child in self.children.values():
            child.update(update_hmap=copy.deepcopy(self.update_hmap))

        if self.update_hmap:
            self.update_hmap = False

    def hmap(self, dataset, prev_dataset):

        if dataset.update_hmap:
            prev_dataset.data = dataset.all_data
            
            if 'Bwd' in prev_dataset.name:
                try:
                    prev_dataset.data = np.fliplr(prev_dataset.data)
                except ValueError:
                    prev_dataset.data = np.flip(prev_dataset.data)


class HeatMap(Dataset):

    def visualize(self, graph, **kwargs):
        
        self.graph = pg.ImageView(view=pg.PlotItem())
        self.gui.graph_layout.addWidget(self.graph)
        self.graph.show()
        self.graph.view.setAspectLocked(False)
        self.graph.view.invertY(False)
        self.graph.setPredefinedGradient('inferno')
        if set(['min', 'max', 'pts']).issubset(kwargs.keys()):
            self.min, self.max, self.pts = kwargs['min'], kwargs['max'], kwargs['pts']
            self.graph.view.setLimits(xMin=kwargs['min'], xMax=kwargs['max'])

    def update(self, **kwargs):
        
        if 'update_hmap' in kwargs and kwargs['update_hmap']:
            try:
                if hasattr(self, 'min'):
                    self.graph.setImage(
                        img=np.transpose(self.data),
                        autoRange=False,
                        scale=((self.max-self.min)/self.pts,1),
                        pos=(self.min, 0)
                    )
                else:
                    self.graph.setImage(
                        img=np.transpose(self.data),
                        autoRange=False
                    )
            except:
                pass

    def save(self, filename=None, directory=None, date_dir=True):

        generic_save(
            data=self.data,
            filename=f'{filename}_{self.name}',
            directory=directory,
            date_dir=date_dir
        )
        if self.x is not None:
            generic_save(
                data=self.x,
                filename=f'{filename}_{self.name}_x',
                directory=directory,
                date_dir=date_dir
            )

        if hasattr(self, 'graph'):
            pyqtgraph_save(
                self.graph.getView(),
                f'{filename}_{self.name}',
                directory,
                date_dir
            )

        for child in self.children.values():
            child.save(filename, directory, date_dir)

        save_metadata(self.log, filename, directory, date_dir)


class LockedCavityScan1D(TriangleScan1D):

    def __init__(self, *args, **kwargs):

        self.t0 = time.time()
        self.v = None
        super().__init__(*args, **kwargs)
    
    def fill_params(self, config):

        super().fill_params(config)
        if not self.backward:
            self.add_child(
                name='Cavity lock',
                data_type=Dataset
            )
            self.add_child(
                name='Cavity history',
                data_type=InfiniteRollingLine,
                data_length=10000
            )
            self.add_params_to_gui(
                voltage=0.0
            )

    def set_v(self, v):
        """ Updates voltage """

        self.v = v
        self.widgets['voltage'].setValue(self.v)
        self.children['Cavity history'].set_data(self.v)

# Useful mappings

def moving_average(dataset, prev_dataset=None):
	n=20
	ret = np.cumsum(dataset.data)
	ret[n:] = ret[n:] - ret[:-n]
	prev_dataset.set_data(data=ret[n-1:]/n)