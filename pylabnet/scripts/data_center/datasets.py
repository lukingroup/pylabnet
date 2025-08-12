from numpy.lib.function_base import kaiser
import pyqtgraph as pg
import numpy as np
import copy
import time
from PyQt5 import QtWidgets, QtCore

from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget
from pylabnet.gui.pyqt.external_gui import Window, ParameterPopup, GraphPopup, Confluence_support_GraphPopup, Confluence_Handler, GraphPopupTabs, Confluence_support_GraphPopupTabs
from pylabnet.utils.logging.logger import LogClient, LogHandler
from pylabnet.utils.helper_methods import save_metadata, generic_save, npy_generic_save, pyqtgraph_save, fill_2dlist, TimeAxisItem

import sys


def get_color_index(dataset, kwargs):

    if 'color_index' in kwargs:
        color_index = kwargs['color_index']
    else:

        try:
            tabs_enabled = dataset.gui.windows[kwargs['window']].tabs_enabled

        # If Window has not tabs
        except AttributeError:
            tabs_enabled = False

        # If dataset is initial dataset
        except KeyError:
            tabs_enabled = False

        if tabs_enabled:
            color_index = dataset.gui.windows[kwargs['window']].num_tabs - 1
        elif 'window' in kwargs:
            color_index = dataset.gui.windows[kwargs['window']].graph_layout.count() - 1
        else:
            color_index = dataset.gui.graph_layout.count() - 1

    return color_index


class Dataset():

    def __init__(self, gui: Window, log: LogClient = None, data=None,
                 x=None, graph=None, name=None, dont_clear=False, enable_confluence=True, **kwargs):
        """ Instantiates an empty generic dataset

        :param gui: (Window) GUI window for data graphing
        :param log: (LogClient)
        :param data: initial data to set
        :param x: x axis
        :param graph: (pg.PlotWidget) graph to use
        :param confluence, instances of confluence_handler class - handle confluence things.
        """

        self.log = LogHandler(log)
        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}

        if(log is None):
            self.metadata = None
        else:
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

        # Initialize input and output dicts
        self._input_dict = None
        self._output_dict = None

        # Flag indicating whether data should be
        self.dont_clear = dont_clear

        # Confluence handler and its button
        app = QtWidgets.QApplication.instance()
        if app is None:
            self.app = QtWidgets.QApplication(sys.argv)
        else:
            self.log.info('QApplication instance already exists: %s' % str(app))
            self.app = app

        self.confluence_handler = None

        self.enable_confluence = enable_confluence

        if(log == None):
            self.enable_confluence = False

        # Configure data visualization
        self.gui = gui
        self.visualize(graph, **kwargs)

        # Property which defines whether dataset is important, i.e. should it be saved in a separate dataset
        self.is_important = False

        # For large-sized data, saving as npy is more efficient
        self.save_as_npy = False

        return

    def set_input_dict(self, input_dict):

        # save to metadata
        self.log.update_metadata(
            input_dict=input_dict
        )

        self._input_dict = input_dict

    def get_input_parameter(self, varname):
        return list(self._input_dict[varname].values())[0]

    def set_output_dict(self, output_dict):
        self._output_dict = output_dict

    def get_output_dict(self):
        return self._output_dict

    def update_setting(self):
        self.confluence_handler.confluence_popup.Popup_Update()

    def upload_pic(self):
        self.confluence_handler.confluence_popup.Popup_Upload()
        return

    def add_child(self, name, mapping=None, data_type=None,
                  new_plot=True, dont_clear=False, **kwargs):
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
            dont_clear=dont_clear,
            log=self.log,
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

        self.handle_new_window(graph, **kwargs)

        color_index = get_color_index(self, kwargs)

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                np.mod(color_index, len(self.gui.COLOR_LIST))
            ])
        )
        # self.update(**kwargs)

    def clear_data(self):
        self.data = None
        self.curve.setData([])
    #test
    # Note: This recursive code could potentially run into infinite iteration problem.

    def clear_all_data(self):
        """ Calls function to clear own data and goes through children to clear their data """

        if not self.dont_clear:
            self.clear_data()
            self.update()

        for child in self.children.values():
            child.clear_all_data()

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

    def save(self, filename=None, directory=None, date_dir=True, unique_id=None):
        if not self.save_as_npy:

            generic_save(
                data=self.data,
                filename=f'{filename}_{self.name}_{unique_id}',
                directory=directory,
                date_dir=date_dir
            )
            if self.x is not None:
                generic_save(
                    data=self.x,
                    filename=f'{filename}_{self.name}_x_{unique_id}',
                    directory=directory,
                    date_dir=date_dir
                )

            if hasattr(self, 'graph'):
                pyqtgraph_save(
                    self.graph.getPlotItem(),
                    f'{filename}_{self.name}_{unique_id}',
                    directory,
                    date_dir
                )

            # if the dataset is important, save it again in the important dataset folder.
            if self.is_important:
                generic_save(
                    data=self.data,
                    filename=f'{filename}_{self.name}_{unique_id}',
                    directory=directory + "\\important_data",
                    date_dir=date_dir
                )
                if self.x is not None:
                    generic_save(
                        data=self.x,
                        filename=f'{filename}_{self.name}_x_{unique_id}',
                        directory=directory + "\\important_data",
                        date_dir=date_dir
                    )

                if hasattr(self, 'graph'):
                    pyqtgraph_save(
                        self.graph.getPlotItem(),
                        f'{filename}_{self.name}_{unique_id}',
                        directory + "\\important_data",
                        date_dir
                    )

            for child in self.children.values():
                child.save(filename, directory, date_dir, unique_id)

        else:
            # save as npy (for large-sized data, and don't save graph file)
            npy_generic_save(
                data=self.data,
                filename=f'{filename}_{self.name}_{unique_id}',
                directory=directory,
                date_dir=date_dir
            )
            if self.x is not None:
                npy_generic_save(
                    data=self.x,
                    filename=f'{filename}_{self.name}_x_{unique_id}',
                    directory=directory,
                    date_dir=date_dir
                )
    
            # if the dataset is important, save it again in the important dataset folder.
            if self.is_important:
                npy_generic_save(
                    data=self.data,
                    filename=f'{filename}_{self.name}_{unique_id}',
                    directory=directory + "\\important_data",
                    date_dir=date_dir
                )
                if self.x is not None:
                    npy_generic_save(
                        data=self.x,
                        filename=f'{filename}_{self.name}_x_{unique_id}',
                        directory=directory + "\\important_data",
                        date_dir=date_dir
                    )
    
            for child in self.children.values():
                child.save(filename, directory, date_dir, unique_id)

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
                self.widgets[name].valueChanged.connect(
                    lambda state, obj=self, name=name: setattr(obj, name, state)
                )
            elif type(value) is float:
                self.widgets[name] = QtWidgets.QDoubleSpinBox()
                self.widgets[name].setMaximum(1000000000.)
                self.widgets[name].setMinimum(-1000000000.)
                self.widgets[name].setDecimals(6)
                self.widgets[name].setValue(value)
                self.widgets[name].valueChanged.connect(
                    lambda state, obj=self, name=name: setattr(obj, name, state)
                )
            else:
                self.widgets[name] = QtWidgets.QLabel(str(value))
            setattr(self.gui, name, self.widgets[name])

            hbox.addWidget(self.widgets[name])
            self.gui.dataset_layout.addLayout(hbox)

        self.gui.initialize_step_sizes()

    def handle_new_window(self, graph, **kwargs):
        """ Handles visualizing and possibility of new popup windows """

        if graph is None:
            # If we want to use a separate window

            if 'window' in kwargs:
                # Check whether this window exists
                if not kwargs['window'] in self.gui.windows:

                    # Check if we want to enable tabs
                    if 'tabs_enabled' in kwargs:
                        tabs_enabled = kwargs['tabs_enabled']

                        if 'tablabel' in kwargs:
                            tablabel = kwargs["tablabel"]
                        else:
                            tablabel = "Tab"
                    else:
                        tabs_enabled = False

                    if 'window_title' in kwargs:
                        window_title = kwargs['window_title']
                    else:
                        window_title = 'Graph Holder'

                    # self.gui.windows[kwargs['window']] = GraphPopup(
                    #     window_title=window_title, size=(700, 300))

                    if(self.enable_confluence):
                        if tabs_enabled:

                            self.gui.windows[kwargs['window']] = Confluence_support_GraphPopupTabs(
                                app=None, gui=self.gui, log=self.log, window_title=window_title, size=(1000, 500), tablabel=tablabel
                            )

                            self.gui.windows[kwargs['window']].tabs_enabled = True
                        else:
                            self.gui.windows[kwargs['window']] = Confluence_support_GraphPopup(
                                app=None, gui=self.gui, log=self.log, window_title=window_title, size=(1000, 500)
                            )
                            self.gui.windows[kwargs['window']].tabs_enabled = False
                    elif tabs_enabled:
                        self.gui.windows[kwargs['window']] = GraphPopupTabs(
                            window_title=window_title, size=(700, 300), tablabel=tablabel
                        )
                    else:
                        self.gui.windows[kwargs['window']] = GraphPopup(
                            window_title=window_title, size=(700, 300),
                        )

                        self.gui.windows[kwargs['window']].tabs_enabled = False

                     # Window already exists
                else:
                    # Check if we want to enable tabs
                    tabs_enabled = self.gui.windows[kwargs['window']].tabs_enabled

                if('datetime_axis' in kwargs and kwargs['datetime_axis']):
                    date_axis = TimeAxisItem(orientation='bottom')
                    self.graph = pg.PlotWidget(axisItems={'bottom': date_axis})
                else:
                    self.graph = pg.PlotWidget()

                if tabs_enabled:

                    num_tabs = self.gui.windows[kwargs['window']].num_tabs

                    if 'tablabel' in kwargs:
                        tablabel = kwargs["tablabel"]
                    else:
                        tablabel = f"Tab{num_tabs}"

                    tab_widget_labels = [self.gui.windows[kwargs['window']].tabs.tabText(i) for i in range(num_tabs)]

                    if tablabel in tab_widget_labels:
                        tab_widget_graphlayout = self.gui.windows[kwargs['window']].tabs.widget(tab_widget_labels.index(tablabel)).GraphLayout

                        # add to retrieved tab
                        tab_widget_graphlayout.addWidget(
                            self.graph
                        )

                    elif num_tabs == 0:

                        # add to first tab
                        self.gui.windows[kwargs['window']].tab1.GraphLayout.addWidget(
                            self.graph
                        )
                        self.gui.windows[kwargs['window']].num_tabs += 1

                    else:
                        self.gui.windows[kwargs['window']].add_graph_to_new_tab(
                            graph=self.graph,
                            label=tablabel
                        )
                else:

                    self.gui.windows[kwargs['window']].graph_layout.addWidget(self.graph)

            # Otherwise, add a graph to the main layout
            else:

                if('datetime_axis' in kwargs and kwargs['datetime_axis']):
                    self.graph = self.gui.add_graph(datetime_axis=True)
                else:
                    self.graph = self.gui.add_graph()

            self.graph.getPlotItem().setTitle(self.name)

        # Reuse a PlotWidget if provided
        else:
            self.graph = graph


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
        self.presel_success_indicator = pg.SpinBox(value=0.0)
        self.presel_success_indicator.setStyleSheet('font-size: 12pt')
        self.presel_success_value = 0
        super().__init__(*args, **kwargs)
        self.add_child(name='Single Trace', mapping=self.recent, data_type=Dataset)
        if 'presel_params' in self.config:
            self.presel_params = self.config['presel_params']
            self.fill_parameters(self.presel_params)
        else:
            self.presel_params = None
            self.setup_preselection(threshold=float, less_than=str, avg_values=int)
        if 'presel_data_length' in self.config:
            presel_data_length = self.config['presel_data_length']
        else:
            presel_data_length = None

        hbox = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel('Recent preselection average: ')
        label.setStyleSheet('font-size: 12pt')
        hbox.addWidget(label)
        hbox.addWidget(self.presel_success_indicator)
        self.gui.graph_layout.addLayout(hbox)
        self.add_child(
            name='Preselection Counts',
            data_type=InfiniteRollingLine,
            data_length=presel_data_length
        )
        self.line = self.children['Preselection Counts'].graph.getPlotItem().addLine(y=self.presel_params['threshold'])

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
        self.log.update_metadata(presel_params=self.presel_params)
        self.add_params_to_gui(**self.presel_params)

        self.widgets['threshold'].valueChanged.connect(self.update_threshold)

    def preselect(self, dataset, prev_dataset):
        """ Preselects based on user input parameters """

        if self.presel_params['less_than'] == 'True':
            if dataset.children['Preselection Counts'].data[-1] < self.presel_params['threshold']:
                dataset.preselection = True
                if prev_dataset.data is None:
                    prev_dataset.data = dataset.recent_data
                else:
                    prev_dataset.data += dataset.recent_data
            else:
                dataset.preselection = False
        else:
            if dataset.children['Preselection Counts'].data[-1] > self.presel_params['threshold']:
                dataset.preselection = True
                if prev_dataset.data is None:
                    prev_dataset.data = dataset.recent_data
                else:
                    prev_dataset.data += dataset.recent_data
            else:
                dataset.preselection = False

        # Calculate most recent preselection value

        presel_trace = dataset.children['Preselection Counts'].data
        presel_trace_len = len(presel_trace)
        if presel_trace_len > 0:
            if self.presel_params['avg_values'] > presel_trace_len:
                self.presel_success_value = np.mean(presel_trace)
            else:
                self.presel_success_value = np.mean(presel_trace[-self.presel_params['avg_values']:])

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

    def update(self, **kwargs):

        self.presel_success_indicator.setValue(self.presel_success_value)
        super().update(**kwargs)

    def update_threshold(self, threshold: float):
        """ Updates the threshold to a new value

        :param threshold: (float) new value of threshold
        """

        setattr(self, 'threshold', threshold)
        self.presel_params['threshold'] = threshold
        self.line.setValue(self.presel_params['threshold'])

    @staticmethod
    def recent(dataset, prev_dataset):
        prev_dataset.data = dataset.recent_data


class InvisibleData(Dataset):
    """ Dataset which does not plot """

    def visualize(self, graph, **kwargs):
        self.curve = pg.PlotDataItem()


class InvisibleRollingData(Dataset):
    """ Dataset which does not plot, setting data does not replace the data but appends like InfiniteRollingLine. """

    def visualize(self, graph, **kwargs):
        self.curve = pg.PlotDataItem()

    def set_data(self, data):
        """ Updates data
        :param data: (scalar or array) data to add
        """

        if self.data is None:
            if np.isscalar(data):
                self.data = np.array([data])
            else:
                self.data = np.array(data)
        else:
            self.data = np.append(self.data, data)


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

        :param data: (scalar or array) data to add
        """

        if self.data is None:
            if(np.isscalar(data)):
                self.data = np.array([data])
            else:
                self.data = np.array(data)
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


class time_trace_monitor(RollingLine):
    def __init__(self, *args, **kwargs):
        if('data_length' not in kwargs):
            kwargs['data_length'] = "just to bypass the popup window and the datalength will be set up later"
        kwargs['datetime_axis'] = True
        super().__init__(*args, **kwargs)

    def set_data(self, data):
        """ Updates data

        :param data: (scalar) data to add
        """
        dt_timestamp = time.time()

        if self.data is None:
            self.data = np.array([data])

        else:
            if len(self.data) >= self.data_length:
                self.data = np.append(self.data, data)[-1 * self.data_length:]
            else:
                self.data = np.append(self.data, data)

        if self.x is None:
            self.x = np.array([dt_timestamp])

        else:
            if len(self.x) >= self.data_length:
                self.x = np.append(self.x, dt_timestamp)[-1 * self.data_length:]
            else:
                self.x = np.append(self.x, dt_timestamp)

        for name, child in self.children.items():
            # If we need to process the child data, do it
            if name in self.mapping:
                self.mapping[name](self, prev_dataset=child)


class ManualOpenLoopScan(Dataset):

    def __init__(self, *args, **kwargs):

        self.args = args
        self.kwargs = kwargs
        self.stop = False

        kwargs['name'] = 'Raw Counts'

        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}
        self.kwargs.update(self.config)

        super().__init__(*self.args, **self.kwargs)

        self.add_child(
            name='Smooth counts',
            mapping=self.smooth_data,
            data_type=Dataset
        )

        self.add_child(
            name='Wavelength',
            data_type=InfiniteRollingLine,
            data_length=1000
        )

        # Get scan parameters from config
        if set(['integration', 'max_runs', 'bins_per_ghz', 'min_bins']).issubset(self.kwargs.keys()):
            self.fill_params(self.kwargs)

        else:
            self.log.error('Please provide config file parameters "delay", "max_runs", "bins_per_ghz", and "min_bins.')

    def fill_params(self, config):
        """ Fills the min max and pts parameters """
        self.integration, self.max_runs, self.bins_per_ghz, self.min_bins = config['integration'], config['max_runs'], config['bins_per_ghz'], config['min_bins']
        # Questions: Why is this line necessary for the plot to appear.
        self.kwargs.update(dict(
            x=np.linspace(400, 500, 100),
            name='Fwd trace'
        ))

    def visualize(self, graph, **kwargs):
        self.handle_new_window(graph, **kwargs)

        color_index = get_color_index(self, kwargs)

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                np.mod(color_index, len(self.gui.COLOR_LIST))
            ]),
            symbol='o',
            symbolPen=pg.mkPen(self.gui.COLOR_LIST[
                np.mod(color_index, len(self.gui.COLOR_LIST))
            ]),
            symbolBrush=pg.mkBrush(self.gui.COLOR_LIST[
                np.mod(color_index, len(self.gui.COLOR_LIST))
            ]),
            downsample=0.5,
            downsampleMethod='mean'
        )
        self.update(**kwargs)

    def set_data(self, data=None, x=None, wavelength=None):
        """ Sets the data for a new round of acquisition

        :param data: histogram data from latest acquisition
            note the histogram should have been cleared prior to acquisition
        :param x: x axis for data
        :param wavelength: (float) value of acquired wavelength
        """

        # Add wavelength to aux monitor.
        self.children['Wavelength'].set_data(wavelength)

        # Append new data.
        if self.data is None:
            self.data = np.array([data])

        else:
            self.data = np.append(self.data, data)

        if self.x is None:
            self.x = np.array([x])

        else:
            self.x = np.append(self.x, x)

        # Re-order array
        self.data = self.data[np.argsort(self.x)]
        self.x = self.x[np.argsort(self.x)]

        # Add data to parent dataset.
        super().set_data(self.data, self.x)

    def smooth_data(self, dataset, prev_dataset):

        previous_x = dataset.x
        previous_y = dataset.data

        data_len = len(previous_y)
        scan_span = ((previous_x[-1] - previous_x[0]) * 1e3)
        current_bins_per_ghz = data_len / scan_span

        # self.log.info(f'Scan span = {scan_span}')
        # self.log.info(f'current_bins_per_ghz = {current_bins_per_ghz}')
        # self.log.info(f'self.bins_per_ghz = {self.bins_per_ghz}')

        new_num_bins = int(scan_span * self.bins_per_ghz)
        #self.log.info(f'new_num_bins = {new_num_bins}')

        if current_bins_per_ghz < self.bins_per_ghz or scan_span < 0.001 or new_num_bins < self.min_bins:
            prev_dataset.data = previous_y
            prev_dataset.x = previous_x
        else:

            self.log.info(f'new_num_bins = {new_num_bins}')
            self.log.info(f'data_len = {data_len}')

            padded_x = np.pad(previous_x, (0, new_num_bins - data_len % new_num_bins), 'constant')
            padded_y = np.pad(previous_y, (0, new_num_bins - data_len % new_num_bins), 'constant')

            binlength = int(len(padded_x) / new_num_bins)

            # Rebin arrays
            rebinned_x = np.zeros(new_num_bins)
            rebinned_y = np.zeros(new_num_bins)

            # Tranform 0s to Nan so they don't change the mean values.
            padded_x[padded_x == 0] = np.nan
            padded_y[padded_y == 0] = np.nan

            for i in range(new_num_bins):
                # Sum counts
                rebinned_y[i] = np.sum(padded_y[i * binlength:(i + 1) * binlength])
                # Average wavelength
                rebinned_x[i] = np.average(padded_x[i * binlength:(i + 1) * binlength])

            # Remove nans.
            nan_index = ~np.isnan(rebinned_x)
            self.log.info(nan_index)

            rebinned_x = rebinned_x[nan_index]
            rebinned_y = rebinned_y[nan_index]

            prev_dataset.data = rebinned_y[:-1]
            prev_dataset.x = rebinned_x[:-1]


class LockMonitor(Dataset):

    def __init__(self, *args, **kwargs):

        self.args = args
        self.kwargs = kwargs
        self.stop = False

        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}
        self.kwargs.update(self.config)

        self.v = None
        self.rp_pid_gate = None

        super().__init__(*self.args, **self.kwargs)

        # Add child for PD current
        self.add_child(
            name='Piezo Voltage',
            data_type=InfiniteRollingLine,
            data_length=10000,
            color_index=4
        )

        # Add child for PD current
        self.add_child(
            name='PD Transmission',
            data_type=InfiniteRollingLine,
            data_length=10000,
            color_index=4
        )
        self.add_child(
            name='Demodulated PD Transmission',
            data_type=InfiniteRollingLine,
            data_length=10000,
            color_index=4
        )
        self.add_child(
            name='Cavity lock',
            data_type=Dataset,
            window='lock_monitor',
            window_title='Cavity lock monitor',
            color_index=3
        )
        self.add_child(
            name='Cavity history',
            data_type=InfiniteRollingLine,
            data_length=10000,
            window='lock_monitor',
            color_index=4
        )
        self.add_child(
            name='Max count history',
            data_type=InfiniteRollingLine,
            data_length=10000,
            window='lock_monitor',
            color_index=5
        )

    def set_v_and_counts(self, v, counts):
        """ Updates voltage and counts"""
        self.v = v
        # self.widgets['voltage'].setValue(self.v)
        self.children['Cavity history'].set_data(self.v)
        self.children['Max count history'].set_data(counts)

    def set_pd_demod_piezo_voltage(self, pd_voltage, demod_voltage, piezo_voltage):
        self.children['PD Transmission'].set_data(pd_voltage)
        self.children['Demodulated PD Transmission'].set_data(demod_voltage)
        self.children['Piezo Voltage'].set_data(piezo_voltage)


class Scatterplot(Dataset):
    def visualize(self, graph, **kwargs):
        self.handle_new_window(graph, **kwargs)

        self.curve = pg.ScatterPlotItem(x=[0], y=[0])
        self.graph.addItem(self.curve)
        self.update(**kwargs)

    def clear_data(self):
        self.data = None
        self.curve.setData([])
        self.graph.clear()


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
        self.kwargs.update(self.config)

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

        pass_kwargs = dict()
        if 'window' in config:
            pass_kwargs['window'] = config['window']

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
            pts=self.pts,
            **pass_kwargs
        )

        # Add child for backward plot
        if not self.backward:
            self.add_child(
                name='Bwd trace',
                min=self.min,
                max=self.max,
                pts=self.pts,
                backward=True,
                color_index=1,
                **pass_kwargs
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
                prev_dataset.data[current_index] * (dataset.reps - 1)
                + dataset.data[-1]
            ) / (dataset.reps)
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

    def clear_data(self):

        self.data = None
        self.all_data = None
        self.reps = 1


class SawtoothScan1D(Dataset):
    """ 1D Sawtooth sweep of a parameter """

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
        self.kwargs.update(self.config)

        # Get scan parameters from config
        if set(['min', 'max', 'pts']).issubset(self.kwargs.keys()):
            self.fill_params(self.kwargs)

        # Prompt user if not provided in config
        else:
            self.popup = ParameterPopup(min=float, max=float, pts=int, name=str)
            self.popup.parameters.connect(self.fill_params)

    def fill_params(self, config):
        """ Fills the min max and pts parameters """

        self.min, self.max, self.pts = config['min'], config['max'], config['pts']

        self.kwargs.update(dict(
            x=np.linspace(self.min, self.max, self.pts),
            name=config['name'] + 'trace'
        ))
        super().__init__(*self.args, **self.kwargs)

        pass_kwargs = dict()
        if 'window' in config:
            pass_kwargs['window'] = config['window']
        if 'window_title' in config:
            pass_kwargs['window_title'] = config['window_title']

        # Add child for averaged plot
        self.add_child(
            name=config['name'] + 'avg',
            mapping=self.avg,
            data_type=Dataset,
            new_plot=False,
            x=self.x,
            color_index=2
        )

        # Add child for HMAP
        self.add_child(
            name=config['name'] + 'scans',
            mapping=self.hmap,
            data_type=HeatMap,
            min=self.min,
            max=self.max,
            pts=self.pts,
            **pass_kwargs
        )

    def avg(self, dataset, prev_dataset):
        """ Computes average dataset (mapping) """

        # If we have already integrated a full dataset, avg
        if dataset.reps > 1:
            current_index = len(dataset.data) - 1
            prev_dataset.data[current_index] = float((
                float(prev_dataset.data[current_index]) * (float(dataset.reps) - 1)
                + float(dataset.data[-1])
            ) / float(dataset.reps))
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

    def clear_data(self):

        self.data = None
        self.all_data = None
        self.reps = 1


class SawtoothScan1D_array_update(SawtoothScan1D):
    """ 1D Sawtooth sweep of a parameter, but accept an array update (more efficient) """

    def avg(self, dataset, prev_dataset):
        """ Computes average dataset (mapping) """

        # If we have already integrated a full dataset, avg
        # only update when full scan finishes
        if dataset.reps > 1:
            current_data_len = len(dataset.data)

            if(current_data_len == 0):
                prev_dataset.data = np.mean(dataset.all_data, axis=0)
        else:
            prev_dataset.data = dataset.data

    def set_data(self, value):

        if(np.isscalar(value)):
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
            return

        if(isinstance(value, np.ndarray)):
            if self.data is None:
                self.reps = 1
                self.data = np.array(value)
            else:
                self.data = np.append(self.data, value)

            if len(self.data) >= self.pts:
                self.update_hmap = True
                self.reps += (len(self.data) // self.pts)

                try:
                    reps_to_do = self.widgets['reps'].value()
                    if reps_to_do > 0 and self.reps > reps_to_do:
                        self.stop = True
                except KeyError:
                    pass

                batch = (len(self.data) // self.pts) * self.pts
                data_stack = self.data[:batch]
                data_rest = self.data[batch:]

                if self.all_data is None:
                    self.all_data = data_stack
                else:
                    self.all_data = np.vstack((self.all_data, data_stack))
                self.data = data_rest

            self.set_children_data()

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None and len(self.data) <= len(self.x):
            self.curve.setData(self.x[:len(self.data)], self.data)
        if(isinstance(self.data, np.ndarray)):
            for child in self.children.values():
                child.update(update_hmap=copy.deepcopy(self.update_hmap))

        if self.update_hmap:
            self.update_hmap = False


class HeatMap(Dataset):

    def visualize(self, graph, **kwargs):

        self.handle_new_window(graph, **kwargs)

        self.graph.show()
        self.graph.view.setAspectLocked(False)
        self.graph.view.invertY(False)
        self.graph.setPredefinedGradient('viridis')
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
                        scale=((self.max - self.min) / self.pts, 1),
                        pos=(self.min, 0)
                    )
                else:
                    self.graph.setImage(
                        img=np.transpose(self.data),
                        autoRange=False
                    )
            except:
                pass

    def save(self, filename=None, directory=None, date_dir=True, unique_id=None):

        generic_save(
            data=self.data,
            filename=f'{filename}_{self.name}_{unique_id}',
            directory=directory,
            date_dir=date_dir
        )
        if self.x is not None:
            generic_save(
                data=self.x,
                filename=f'{filename}_{self.name}_x_{unique_id}',
                directory=directory,
                date_dir=date_dir
            )

        if hasattr(self, 'graph'):
            pyqtgraph_save(
                self.graph.getView(),
                f'{filename}_{self.name}_{unique_id}',
                directory,
                date_dir
            )

        for child in self.children.values():
            child.save(filename, directory, date_dir, unique_id)

        save_metadata(self.log, filename, directory, date_dir, unique_id)

    def handle_new_window(self, graph, **kwargs):

        # If we want to use a separate window
        if 'window' in kwargs:

            # # Check whether this window exists
            if not hasattr(self.gui, kwargs['window']):
                self.log.info('Graph Holder already exists!!!!!!!!!!')

            if 'window_title' in kwargs:
                window_title = kwargs['window_title']
            else:
                window_title = 'Graph Holder'
            setattr(
                self.gui,
                kwargs['window'],
                GraphPopup(window_title=window_title)
            )

            self.graph = pg.ImageView(view=pg.PlotItem())
            getattr(self.gui, kwargs['window']).graph_layout.addWidget(
                self.graph
            )

        # Otherwise, add a graph to the main layout
        else:
            self.graph = pg.ImageView(view=pg.PlotItem())
            self.gui.graph_layout.addWidget(self.graph)

    def clear_data(self):

        self.data = None
        self.graph.clear()


class Plot2D(Dataset):
    """ Plots a 2D dataset on a 2D color plot. Plots only the latest value and overwrites if more data is added"""

    def visualize(self, graph, **kwargs):

        self.handle_new_window(graph, **kwargs)

        self.graph.show()
        self.graph.view.setAspectLocked(False)
        self.graph.view.invertY(False)
        self.graph.setPredefinedGradient('viridis')

        self.min_x, self.max_x, self.pts_x = kwargs['min_x'], kwargs['max_x'], kwargs['pts_x']
        self.min_y, self.max_y, self.pts_y = kwargs['min_y'], kwargs['max_y'], kwargs['pts_y']

        self.data = np.zeros([self.pts_y, self.pts_x])
        self.data[:] = np.nan
        self.position = 0

        self.graph.view.setLimits(xMin=kwargs['min_x'], xMax=kwargs['max_x'], yMin=kwargs['min_y'], yMax=kwargs['max_y'])

    def update(self, **kwargs):

        if not np.isnan(self.data).all():
            self.graph.setImage(
                img=np.transpose(self.data),
                autoRange=False,
                scale=((self.max_x - self.min_x) / self.pts_x, (self.max_y - self.min_y) / self.pts_y),
                pos=(self.min_x, self.min_y)
            )

        for child in self.children.values():
            child.update(**kwargs)

    def set_data(self, value):

        try: # check if data is an array and what its shape is
            shape = value.shape

            if len(shape) == 0: # data is single value
                x = np.mod(self.position, self.pts_x)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                self.data[y, x] = value
                self.position += 1
            if len(shape) == 1:
                if shape[0] == 1: # data is single value
                    x = np.mod(self.position, self.pts_x)
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, x] = value
                    self.position += 1
                elif shape[0] == self.pts_x:  # data is one row of the total 2D dataset matrix
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, :] = value
                    self.position += self.pts_x
                else:
                    self.log.error(f'Incompatible data shape: expected (1, ) or ({self.pts_x}, ), got ({shape[0]}, )')

            elif len(shape) == 2: # data contains total 2D dataset matrix
                if (shape[0] == self.pts_x) and (shape[1] == self.pts_y):
                    self.data = np.transpose(value)
                    self.position += self.pts_x * self.pts_y
                elif (shape[1] == self.pts_x) and (shape[0] == self.pts_y):
                    self.data = value
                    self.position += self.pts_x * self.pts_y
                else:
                    self.log.error(f'Incompatible data shape: expected ({self.pts_x}, {self.pts_y}), got ({shape[0]}, {shape[1]})')
            else:
                self.log.error(f'Incompatible data shape: expected 1D or 2D, got {len(shape)}D')

        except AttributeError: # data is not an array. Check if it is list or float, int
            try: # check if data is list
                data_length = len(value)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                if data_length == 1: # data is single value
                    x = np.mod(self.position, self.pts_x)
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, x] = value[o]
                    self.position += 1
                elif data_length == self.pts_x:  # data (list) is one row of the total 2D dataset matrix
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    for ii in range(self.pts_x):
                        self.data[y, ii] = value[ii]
                    self.position += self.pts_x
                else:
                    self.log.error(f'Incompatible data length: expected 1 or {self.pts_x}, got {data_length}')
            except TypeError: # data is not list. Data is float or int
                x = np.mod(self.position, self.pts_x)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                self.data[y, x] = value
                self.position += 1

    def save(self, filename=None, directory=None, date_dir=True, unique_id=None):

        # save axes
        x = np.linspace(self.min_x, self.max_x, self.pts_x)
        y = np.linspace(self.min_y, self.max_y, self.pts_y)

        generic_save(data=x,
                     filename=f'{filename}_{self.name}_x_{unique_id}',
                     directory=directory,
                     date_dir=date_dir
                     )
        generic_save(data=y,
                     filename=f'{filename}_{self.name}_y_{unique_id}',
                     directory=directory,
                     date_dir=date_dir
                     )

        generic_save(data=self.data,
                     filename=f'{filename}_{self.name}_{unique_id}',
                     directory=directory,
                     date_dir=date_dir
                     )

        if hasattr(self, 'graph'):
            pyqtgraph_save(
                self.graph.getView(),
                f'{filename}_{self.name}_{unique_id}',
                directory,
                date_dir
            )

        for child in self.children.values():
            child.save(filename, directory, date_dir, unique_id)

        save_metadata(self.log, filename, directory, date_dir, unique_id)

    def handle_new_window(self, graph, **kwargs):

        # If we want to use a separate window
        if 'window' in kwargs:

            # Check whether this window exists
            if not hasattr(self.gui, kwargs['window']):

                if 'window_title' in kwargs:
                    window_title = kwargs['window_title']
                else:
                    window_title = 'Graph Holder'
                setattr(
                    self.gui,
                    kwargs['window'],
                    GraphPopup(window_title=window_title)
                )

            self.graph = pg.ImageView(view=pg.PlotItem())
            getattr(self.gui, kwargs['window']).graph_layout.addWidget(
                self.graph
            )

        # Otherwise, add a graph to the main layout
        else:
            self.graph = pg.ImageView(view=pg.PlotItem())
            self.gui.graph_layout.addWidget(self.graph)

    def clear_data(self):

        self.data = np.zeros([self.pts_y, self.pts_x])
        self.data[:] = np.nan
        self.position = 0
        self.graph.clear()

    def update_colormap(self, cmap):
        self.graph.setPredefinedGradient(cmap)


class Plot2DWithAvg(Plot2D):
    """ Plots a 2D dataset on a 2D color plot. Plots latest value for a given entry as well as average. Stores all data."""

    def __init__(self, *args, **kwargs):

        self.args = args
        self.kwargs = kwargs
        self.all_data = []
        self.stop = False
        if 'config' in kwargs:
            self.config = kwargs['config']
        else:
            self.config = {}
        self.kwargs.update(self.config)

        self.fill_params(self.kwargs)

    def fill_params(self, config):
        """ Fills the min_x,y max_x,y and pts_x,y parameters """

        self.min_x, self.max_x, self.pts_x = config['min_x'], config['max_x'], config['pts_x']
        self.min_y, self.max_y, self.pts_y = config['min_y'], config['max_y'], config['pts_y']

        self.kwargs.update(dict(
            name=config['name'] + 'current'
        ))
        super().__init__(*self.args, **self.kwargs)

        pass_kwargs = dict()
        if 'window' in config:
            pass_kwargs['window'] = config['window']

        # Add child for averaged plot
        self.add_child(
            name=config['name'] + 'avg',
            mapping=self.avg,
            data_type=Plot2D,
            min_x=self.min_x,
            max_x=self.max_x,
            pts_x=self.pts_x,
            min_y=self.min_y,
            max_y=self.max_y,
            pts_y=self.pts_y
        )

        self.children[config['name'] + 'avg'].update_colormap('grey')

    def set_data(self, value):

        try: # check if data is an array and what its shape is
            shape = value.shape

            self.data_shape = shape # pass data shape for averaging

            if len(shape) == 0: # data is single value
                x = np.mod(self.position, self.pts_x)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                self.data[y, x] = value
                self.position += 1
            if len(shape) == 1:
                if shape[0] == 1: # data is single value
                    x = np.mod(self.position, self.pts_x)
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, x] = value
                    self.position += 1
                elif shape[0] == self.pts_x: # data is one row of the total 2D dataset matrix
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, :] = value
                    self.position += self.pts_x
                else:
                    self.log.error(f'Incompatible data shape: expected (1, ) or ({self.pts_x}, ), got ({shape[0]}, )')

            elif len(shape) == 2: # data contains total 2D dataset matrix
                if (shape[0] == self.pts_x) and (shape[1] == self.pts_y):
                    self.data = np.transpose(value)
                    self.position += self.pts_x * self.pts_y
                elif (shape[1] == self.pts_x) and (shape[0] == self.pts_y):
                    self.data = value
                    self.position += self.pts_x * self.pts_y
                else:
                    self.log.error(f'Incompatible data shape: expected ({self.pts_x}, {self.pts_y}), got ({shape[0]}, {shape[1]})')
            else:
                self.log.error(f'Incompatible data shape: expected 1D or 2D, got {len(shape)}D')

        except AttributeError: # data is not an array. Check if it is list or float, int
            try: # check if data is list
                data_length = len(value)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                if data_length == 1: # data is single value
                    self.data_shape = (1,) # pass data shape for averaging
                    x = np.mod(self.position, self.pts_x)
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    self.data[y, x] = value[o]
                    self.position += 1
                elif data_length == self.pts_x:  # data (list) is one row of the total 2D dataset matrix
                    self.data_shape = (self.pts_x,) # pass data shape for averaging
                    y = np.mod(self.position // self.pts_x, self.pts_y)
                    for ii in range(self.pts_x):
                        self.data[y, ii] = value[ii]
                    self.position += self.pts_x
                else:
                    self.log.error(f'Incompatible data length: expected 1 or {self.pts_x}, got {data_length}')
            except TypeError: # data is not list. Data is float or int
                self.data_shape = (1,) # pass data shape for averaging
                x = np.mod(self.position, self.pts_x)
                y = np.mod(self.position // self.pts_x, self.pts_y)
                self.data[y, x] = value
                self.position += 1

        # if a whole dataset matrix has been filled, pass it to all_data to be stored
        if np.mod(self.position, (self.pts_x * self.pts_y)) == 0:
            self.all_data.append(self.data)

        self.set_children_data()

    def save(self, filename=None, directory=None, date_dir=True, unique_id=None):

        # save axes
        x = np.linspace(self.min_x, self.max_x, self.pts_x)
        y = np.linspace(self.min_y, self.max_y, self.pts_y)

        generic_save(data=x,
                     filename=f'{filename}_{self.name}_x_{unique_id}',
                     directory=directory,
                     date_dir=date_dir
                     )
        generic_save(data=y,
                     filename=f'{filename}_{self.name}_y_{unique_id}',
                     directory=directory,
                     date_dir=date_dir
                     )

        self.all_data.append(self.data)
        generic_save(
            data=self.all_data,
            filename=f'{filename}_{self.name}_{unique_id}',
            directory=directory,
            date_dir=date_dir
        )

        if hasattr(self, 'graph'):
            pyqtgraph_save(
                self.graph.getView(),
                f'{filename}_{self.name}_{unique_id}',
                directory,
                date_dir
            )

        for child in self.children.values():
            child.save(filename, directory, date_dir, unique_id)

        save_metadata(self.log, filename, directory, date_dir, unique_id)

    def avg(self, dataset, prev_dataset):
        """ Computes average dataset (mapping) """
        shape = self.data_shape
        if len(shape) == 0: # data is single value
            x = np.mod(self.position - 1, self.pts_x)
            y = np.mod((self.position - 1) // self.pts_x, self.pts_y)
            if (self.position - 1) // (self.pts_x * self.pts_y) == 0:
                prev_dataset.data[y, x] = dataset.data[y, x]
            else:
                n = (self.position - 1) // (self.pts_x * self.pts_y)
                prev_dataset.data[y, x] = (dataset.data[y, x] + n * prev_dataset.data[y, x]) / (n + 1)
        if len(shape) == 1:
            if shape[0] == 1: # data is single value
                x = np.mod(self.position - 1, self.pts_x)
                y = np.mod((self.position - 1) // self.pts_x, self.pts_y)
                if (self.position - 1) // (self.pts_x * self.pts_y) == 0:
                    prev_dataset.data[y, x] = dataset.data[y, x]
                else:
                    n = (self.position - 1) // (self.pts_x * self.pts_y)
                    prev_dataset.data[y, x] = (dataset.data[y, x] + n * prev_dataset.data[y, x]) / (n + 1)
            elif shape[0] == self.pts_x: # data is one row of the total 2D dataset matrix
                y = np.mod((self.position - self.pts_x) // self.pts_x, self.pts_y)
                if (self.position - self.pts_x) // (self.pts_x * self.pts_y) == 0:
                    prev_dataset.data[y, :] = dataset.data[y, :]
                else:
                    n = (self.position - self.pts_x) // (self.pts_x * self.pts_y)
                    prev_dataset.data[y, :] = (dataset.data[y, :] + n * prev_dataset.data[y, :]) / (n + 1)

        if len(shape) == 2: # data contains total 2D dataset matrix
            if ((shape[0] == self.pts_x) and (shape[1] == self.pts_y)) or ((shape[1] == self.pts_x) and (shape[0] == self.pts_y)):
                if (self.position - self.pts_x * self.pts_y) // (self.pts_x * self.pts_y) == 0:
                    prev_dataset.data[:, :] = dataset.data[:, :]
                else:
                    n = (self.position - self.pts_x * self.pts_y) // (self.pts_x * self.pts_y)
                    prev_dataset.data[:, :] = (dataset.data[:, :] + n * prev_dataset.data[:, :]) / (n + 1)

    def clear_data(self):

        self.data = np.zeros([self.pts_y, self.pts_x])
        self.data[:] = np.nan
        self.all_data = []
        self.position = 0
        self.graph.clear()


class LockedCavityScan1D(TriangleScan1D):

    def __init__(self, *args, **kwargs):

        self.t0 = time.time()
        self.v = None
        self.sasha_aom = None
        self.toptica_aom = None

        super().__init__(*args, **kwargs)

    def fill_params(self, config):

        super().fill_params(config)

        if not self.backward:
            self.add_child(
                name='Cavity lock',
                data_type=Dataset,
                window='lock_monitor',
                window_title='Cavity lock monitor',
                color_index=3
            )
            self.add_child(
                name='Cavity history',
                data_type=InfiniteRollingLine,
                data_length=10000,
                window='lock_monitor',
                color_index=4
            ),
            self.add_child(
                name='Max count history',
                data_type=InfiniteRollingLine,
                data_length=10000,
                window='lock_monitor',
                color_index=5
            )
            # self.add_params_to_gui(
            #     voltage=0.0
            # )

    def set_v_and_counts(self, v, counts):
        """ Updates voltage and counts"""

        self.v = v
        # self.widgets['voltage'].setValue(self.v)
        self.children['Cavity history'].set_data(self.v)
        self.children['Max count history'].set_data(counts)

    def clear_data(self):

        # Clear forward/backward scan line
        self.curve.setData([])
        self.data = None

        # Clear retasined data used in heatmaps
        self.all_data = None


class LockedCavityPreselectedHistogram(PreselectedHistogram):

    def __init__(self, *args, **kwargs):

        self.t0 = time.time()
        self.v = None
        self.sasha_aom = None
        self.toptica_aom = None
        self.snspd_7 = None
        self.snspd_8 = None

        super().__init__(*args, **kwargs)

    def fill_parameters(self, params):

        super().fill_parameters(params)
        self.add_child(
            name='Cavity lock',
            data_type=Dataset,
            window='lock_monitor',
            window_title='Cavity lock monitor',
            color_index=3
        )
        self.add_child(
            name='Cavity history',
            data_type=InfiniteRollingLine,
            data_length=10000,
            window='lock_monitor',
            color_index=4
        ),
        self.add_child(
            name='Max count history',
            data_type=InfiniteRollingLine,
            data_length=10000,
            window='lock_monitor',
            color_index=5
        ),
        self.add_child(
            name='Single photons',
            data_type=AveragedHistogram,
            window='photon',
            window_title='Single-photon data'
        )

    def set_v_and_counts(self, v, counts):
        """ Updates voltage and counts"""

        self.v = v
        # self.widgets['voltage'].setValue(self.v)
        self.children['Cavity history'].set_data(self.v)
        self.children['Max count history'].set_data(counts)


class ErrorBarGraph(Dataset):

    def visualize(self, graph, **kwargs):
        """ Prepare data visualization on GUI
        :param graph: (pg.PlotWidget) graph to use
        """

        self.error = None
        self.handle_new_window(graph, **kwargs)

        color_index = get_color_index(self, kwargs)

        self.curve = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(self.gui.COLOR_LIST[
            np.mod(color_index, len(self.gui.COLOR_LIST))
        ]), width=0.5)
        self.error_curve = pg.ErrorBarItem(pen=None, symbol='o', beam=0.5)
        self.graph.addItem(self.curve)
        self.graph.addItem(self.error_curve)
        self.update(**kwargs)

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None:
            if self.x is not None:
                try:
                    width = (self.x[1] - self.x[0]) / 2
                except IndexError:
                    width = 0.5
                self.curve.setOpts(x=self.x, height=self.data, width=width)
            else:
                self.x = np.arange(0, len(self.data))
                self.curve.setOpts(x=self.x, height=self.data, width=0.5)

        if self.error is not None:
            if self.x is not None:
                try:
                    width = (self.x[1] - self.x[0]) / 2
                except IndexError:
                    width = 0.5
                self.error_curve.setData(x=self.x, y=self.data, height=self.error, beam=width)
            else:
                self.error_curve.setData(y=self.data, height=self.error, beam=0.5)

        for child in self.children.values():
            child.update(**kwargs)

    def clear_data(self):

        self.data = None
        self.error = None

        if self.x is not None:
            try:
                width = (self.x[1] - self.x[0]) / 2
            except IndexError:
                width = 0.5
            self.curve.setOpts(x=self.x, height=0 * self.x, width=width)
            self.error_curve.setData(x=self.x, y=0 * self.x, height=0 * self.x, beam=width)
        else:
            self.curve.setOpts(x=[], height=[], width=0.5)
            self.error_curve.setData(x=[], y=[], height=[], beam=0.5)


class ErrorBarAveragedHistogram(ErrorBarGraph):
    """ ErrorBar graph version of AveragedHistogram"""

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


class ErrorBarPlot(Dataset):

    def visualize(self, graph, **kwargs):
        """ Prepare data visualization on GUI

        :param graph: (pg.PlotWidget) graph to use
        """

        self.error = None
        self.handle_new_window(graph, **kwargs)

        color_index = get_color_index(self, kwargs)

        self.curve = pg.ErrorBarItem(pen=pg.mkPen(self.gui.COLOR_LIST[
            np.mod(color_index, len(self.gui.COLOR_LIST))
        ]), symbol='o')
        self.graph.addItem(self.curve)
        self.update(**kwargs)

    def update(self, **kwargs):
        """ Updates current data to plot"""

        if self.data is not None and self.error is not None:
            if self.x is not None:
                try:
                    width = (self.x[1] - self.x[0]) / 2
                except IndexError:
                    width = 0.5
                self.curve.setData(x=self.x, y=self.data, height=self.error, beam=width)
            else:
                self.curve.setData(x=np.arange(len(self.data)), y=self.data, height=self.error, beam=0.5)

        for child in self.children.values():
            child.update(**kwargs)

    def clear_data(self):

        self.data = None
        self.error = None

        if self.x is not None:
            try:
                width = (self.x[1] - self.x[0]) / 2
            except IndexError:
                width = 0.5
            self.curve.setData(x=self.x, y=0 * self.x, height=0 * self.x, beam=width)
        else:
            self.curve.setData(x=[], y=[], height=[], beam=0.5)


class PhotonErrorBarPlot(ErrorBarGraph):
    un_normalized = np.array([])
    normalized = np.array([])
    total_events = 0
    reps = 0

    def visualize(self, graph, **kwargs):
        super().visualize(graph, **kwargs)
        self.add_child(
            name='Photon probabilities, log scale',
            mapping=passthru,
            data_type=Dataset,
            window=kwargs['window']
        )
        self.children['Photon probabilities, log scale'].graph.getPlotItem().setLogMode(False, True)


class InterpolatedMap(Dataset):
    """ Stores a dictionary of 2-tuple coordinates associated with a scalar
    value (e.g. fidelity). When a new datapoint is added, the value at that
    point is updated by averaging with the previous data at that location.
    Plots an interpolated 2D map in a Matplotlib Widget of the acquired datapoints. """

    def __init__(self, *args, **kwargs):
        kwargs['name'] = 'InterpolatedMap'
        super().__init__(*args, **kwargs)

        # Requires SciPy >=1.7.0
        try:
            from scipy.interpolate import RBFInterpolator
        except ImportError as e:
            self.log.warn("This import requires SciPy >=1.7.0.")
            raise(e)

    def set_data(self, data):
        """ Updates data stored in the data dict.

        Datapoints should be in the form ((x, y), z) where (x, y) are
        the coordinate positions and z is the value to be plotted.
        (x, y) are the keys and z is the value in the dict.
        """
        coords, fidelity = data

        # Initialize the data dict
        if self.data is None:
            self.data = {}

        # Place the data into the dictionary, updating the average if already present
        if coords not in self.data:
            self.data[coords] = (1, fidelity)
        else:
            old_N, old_avg = self.data[coords]
            self.data[coords] = (old_N + 1, (old_N * old_avg + fidelity) / (old_N + 1))

    def visualize(self, graph, **kwargs):
        self.handle_new_window(graph, **kwargs)
        self.update(**kwargs)

    def update(self, **kwargs):
        """ Updates current data to plot"""

        # Can't interpolate with too few points
        if self.data is None or len(self.data) < 3:
            return

        # TODO: HELP - how to make this plot update less often??
        import time
        if (int(time.time()) % 5) != 0:
            return

        fig = self.graph.getFigure()
        fig.clf() # Clear figure
        ax = fig.gca()

        # Ignore the first field (# of datapoints at that coord)
        obs_dict = {key: val[1] for key, val in self.data.items()}
        # Extract datapoints as arrays
        coords, fidelities = zip(*obs_dict.items())
        coords = np.array(coords)

        # Compute plotting bounds
        xlims = min(coords[:, 0]), max(coords[:, 0])
        ylims = min(coords[:, 1]), max(coords[:, 1])

        # Create grid for plotting region, imaginary number is part of mgrid() syntax
        n_points = 50
        xgrid = np.mgrid[0.95 * xlims[0]:1.05 * xlims[1]:n_points * 1j, 0.95 * ylims[0]:1.05 * ylims[1]:n_points * 1j]

        # Flatten grid, apply the interpolator to this flattened grid, reshape back to grid
        xflat = xgrid.reshape(2, -1).T
        yflat = RBFInterpolator(coords, fidelities)(xflat)
        ygrid = yflat.reshape(n_points, n_points)

        # Plot interpolated color mesh
        ax.pcolormesh(*xgrid, ygrid, vmin=0.85, vmax=1.0)

        # Plot scatter points
        scatterplot = ax.scatter(*coords.T, c=fidelities, s=50, ec='k', vmin=0.85, vmax=1.0)
        fig.colorbar(scatterplot)

        self.graph.draw()

    def handle_new_window(self, graph, **kwargs):
        """ Handles visualizing and possibility of new popup windows.
        Creates a Matplotlib widget instead of a Pyqtgraph widget. """

        if graph is None:
            # If we want to use a separate window
            if 'window' in kwargs:
                # Check whether this window exists
                if not kwargs['window'] in self.gui.windows:
                    if 'window_title' in kwargs:
                        window_title = kwargs['window_title']
                    else:
                        window_title = 'Graph Holder'

                    self.gui.windows[kwargs['window']] = GraphPopup(
                        window_title=window_title, size=(700, 300)
                    )

                self.graph = MatplotlibWidget()

                self.gui.windows[kwargs['window']].graph_layout.addWidget(
                    self.graph
                )

            # Otherwise, add a graph to the main layout
            else:
                self.graph = self.gui.add_graph()
        # Reuse a PlotWidget if provided
        else:
            self.graph = graph


# Useful mappings

def moving_average(dataset, prev_dataset=None):
    n = 20
    ret = np.cumsum(dataset.data)
    ret[n:] = ret[n:] - ret[:-n]
    prev_dataset.set_data(data=ret[n - 1:] / n)


def passthru(dataset, prev_dataset):
    prev_dataset.set_data(x=dataset.x, data=dataset.data)
