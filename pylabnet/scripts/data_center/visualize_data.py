""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import os
import sys
import importlib
import time
from datetime import datetime
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets


REFRESH_RATE = 150   # refresh rate in ms, try increasing if GUI lags


class DataVisualizer:

    def __init__(self, logger=None, client_tuples=None, config=None, config_name=None):

        self.log = LogHandler(logger)
        self.dataset = None

        # Instantiate GUI window
        self.gui = Window(
            gui_template='data_visualizer',
            host=get_ip()
        )

        # Configure list of experiments
        self.gui.config.setText(config_name)
        self.config = config
        self.bare_data_path = self.config['data_path']
       
        # if self.exp_path is None:
        #     self.exp_path = os.getcwd()
        # sys.path.insert(1, self.exp_path)
        # self.update_experiment_list()

        # sys.path.insert(1, self.data_path)
        self.update_date()

        # Configure button clicks
        self.gui.year_val.textChanged.connect(self.update_date)
        self.gui.month_val.textChanged.connect(self.update_date)
        self.gui.day_val.textChanged.connect(self.update_date)

        self.gui.plot.clicked.connect(self.configure)
        self.gui.save.clicked.connect(self.save)

        self.gui.load_config.clicked.connect(self.reload_config)
        self.gui.showMaximized()
        self.gui.apply_stylesheet()

    def update_date(self):
        year = self.gui.year_val.text()
        month = self.gui.month_val.text()
        day = self.gui.day_val.text()

        self.data_path = self.bare_data_path + "\\" + year + "\\" + month + "\\" + day

        if os.path.isdir(self.data_path):
            self.update_data_list()
        else:
            self.gui.y_data.clear()
            self.gui.x_data.clear()
    
    def update_data_list(self):
        """ Updates list of experiments """

        self.gui.y_data.clear()
        self.gui.x_data.clear()
        for filename in os.listdir(self.data_path):
            if filename.endswith('.txt'):
                self.gui.x_data.addItem(filename[:-4])
                self.gui.y_data.addItem(filename[:-4])
        # self.gui.exp.itemClicked.connect(self.display_experiment)

    def configure(self):
        """ Configures the currently selected experiment + dataset """

        # Load the config
        #self.reload_config()

        # Set all experiments to normal state and highlight configured expt
        # for item_no in range(self.gui.exp.count()):
        #     self.gui.exp.item(item_no).setBackground(QtGui.QBrush(QtGui.QColor('black')))
        # self.gui.exp.currentItem().setBackground(QtGui.QBrush(QtGui.QColor('darkRed')))
        # exp_name = self.gui.exp.currentItem().text()
        # self.module = importlib.import_module(exp_name)
        # self.module = importlib.reload(self.module)

        # Clear graph area and set up new or cleaned up dataset
        for index in reversed(range(self.gui.graph_layout.count())):
            try:
                self.gui.graph_layout.itemAt(index).widget().deleteLater()
            except AttributeError:
                try:
                    self.gui.graph_layout.itemAt(index).layout().deleteLater()
                except AttributeError:
                    pass
        self.gui.windows = {}

        x_data_name =  self.gui.x_data.currentItem().text()
        y_data_name =  self.gui.y_data.currentItem().text()

        x_data = np.loadtxt(self.data_path + "\\" + x_data_name + ".txt")
        y_data = np.loadtxt(self.data_path + "\\" + y_data_name + ".txt")

        thrsh = self.gui.thrsh_val.value()

        plot_method = self.gui.plot_method.currentItem().text()

        if plot_method is None:
            plot_method = "Standard 1D plot (no x-axis)"

        if plot_method == "Standard 1D plot (no x-axis)":
            self.plot_1D(x_data, y_data, x_axis = False)

        if plot_method == "Standard 1D plot":
            self.plot_1D(x_data, y_data, x_axis = True)

        if plot_method == "Thresholded 1D plot (no x-axis)":
            self.plot_1D_thrsh(x_data, y_data, thrsh = thrsh, x_axis = False)

        if plot_method == "Thresholded 1D plot":
            self.plot_1D_thrsh(x_data, y_data, thrsh = thrsh, x_axis = True)
        
        if plot_method == "Histogram":
            self.plot_hist(y_data, thrsh=thrsh)

        
        # If we're not setting up a new measurement type, just clear the data

        # We are reading in the required base-dataset by looking at the define_dataset() as defined in the experiment script.
        # try:
        #     classname = self.module.define_dataset()
        # except AttributeError:
        #     error_msg = "No 'define_dataset' method found in experiment script."
        #     self.log.error("No 'define_dataset' method found in experiment script.")
        #     return

        # try:
        #     self.dataset = getattr(datasets, classname)(
        #         gui=self.gui,
        #         log=self.log,
        #         config=self.config
        #     )
        # except AttributeError:
        #     error_msg = f"Dataset name {classname} as provided in 'define_dataset' method in experiment script is not valid."
        #     self.log.error(error_msg)
        #     return

        # # Run any pre-experiment configuration
        # try:
        #     self.module.configure(dataset=self.dataset, **self.clients)
        # except AttributeError:
        #     pass
        # self.experiment = self.module.experiment

    def plot_1D(self, x=None, y=None, x_axis = False):

        self.create_graph(None)

        color_index = self.gui.graph_layout.count() - 1

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                color_index
            ])
        )

        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y, axis=0)
        else:
            data = y

        if x_axis:
            self.curve.setData(x, data)
        else:
            self.curve.setData(data)
  
    def plot_1D_thrsh(self, x=None, y=None, thrsh=0, x_axis = False):

        self.create_graph(None)

        color_index = self.gui.graph_layout.count() - 1

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                color_index
            ])
        )

        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y>thrsh, axis=0)
        else:
            data = 1*(y>thrsh)

        if x_axis:
            self.curve.setData(x, data)
        else:
            self.curve.setData(data)

    def plot_hist(self, y=None, thrsh=0):

        self.create_graph(None)

        
        color_index_l = self.gui.graph_layout.count() - 1
        self.curve_l = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(self.gui.COLOR_LIST[color_index_l]), width=0.5)

        color_index_h = self.gui.graph_layout.count()
        self.curve_h = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(self.gui.COLOR_LIST[color_index_h]), width=0.5)

        self.graph.addItem(self.curve_l)
        self.graph.addItem(self.curve_h)

        BIN_NUMS = int(np.round(np.max(y)) + 1)

        data, _ = np.histogram(y.flatten(), bins=BIN_NUMS, range=(0, BIN_NUMS-1))

        x = np.arange(0, len(data))
        self.curve_l.setOpts(x=x, height=(x<=thrsh)*data, width=0.5)
        self.curve_h.setOpts(x=x, height=(x>thrsh)*data, width=0.5)

    def create_graph(self, graph, **kwargs):
        """ Creates graph to plot on if it does not exist"""

        if graph is None:
            self.graph = self.gui.add_graph()
        
        # Reuse a PlotWidget if provided
        else:
            self.graph = graph

    def save(self):
        """ Saves data """

        self.log.update_metadata(notes=self.gui.notes.toPlainText())
        filename = self.gui.save_name.text()
        directory = self.config['save_path']
        self.dataset.save(
            filename=filename,
            directory=directory,
            date_dir=True
        )
        save_metadata(self.log, filename, directory, True)
        self.log.info('Data saved')

    def reload_config(self):
        """ Loads a new config file """

        self.config = load_script_config(
            script='data_taker',
            config=self.gui.config.text(),
            logger=self.log
        )


def main():
    control = DataVisualizer(config='preselected_histogram')
    control.gui.app.exec_()


def launch(**kwargs):

    config = load_script_config(
        script='data_visualizer',
        config=kwargs['config'],
        logger=kwargs['logger']
    )

    # Instantiate Monitor script
    control = DataVisualizer(
        logger=kwargs['logger'],
        client_tuples=kwargs['clients'],
        config=config,
        config_name=kwargs['config']
    )
    control.gui.set_network_info(port=kwargs['server_port'])

    # Run continuously
    control.gui.app.exec_()


if __name__ == '__main__':
    main()
