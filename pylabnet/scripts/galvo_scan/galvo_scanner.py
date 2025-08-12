""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import os
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from scipy.optimize import curve_fit

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets
import re


REFRESH_RATE = 150   # refresh rate in ms, try increasing if GUI lags


class GalvoScan:

    def __init__(self, logger=None, client_tuples=None, config=None, config_name=None):

        self.log = LogHandler(logger)
        self.dataset = None

        # Instantiate GUI window
        self.gui = Window(
            gui_template='galvo_scan',
            host=get_ip()
        )

        # Configure list of experiments
        self.gui.config.setText(config_name)
        self.config = config
        self.bare_data_path = self.config['data_path']

        self.graph = None
        self.current_color_index = 0
        self.use_p0 = False
        self.fitting_f = None

        self.update_date()

        # Configure button clicks
        self.gui.year_val.textChanged.connect(self.update_date)
        self.gui.month_val.textChanged.connect(self.update_date)
        self.gui.day_val.textChanged.connect(self.update_date)

        self.gui.x_data_searchbar.textChanged.connect(self.update_data_list)
        self.gui.y_data_searchbar.textChanged.connect(self.update_data_list)
        self.gui.y_match_check.clicked.connect(self.match_data_list)
        self.gui.clear_y_matching.clicked.connect(self.update_data_list)

        self.gui.fit_method.itemClicked.connect(self.update_fit_method)
        self.gui.p0_val.textChanged.connect(self.p0_changed)

        self.gui.plot.clicked.connect(self.plot_data)
        self.gui.clear_data.clicked.connect(self.clear_all_data)

        self.gui.load_config.clicked.connect(self.reload_config)
        self.gui.showMaximized()
        self.gui.apply_stylesheet()

    def update_date(self):
        """ updates what data folder is selected in function of date """
        year = self.gui.year_val.text()
        month = self.gui.month_val.text()
        day = self.gui.day_val.text()

        self.gui.y_data_searchbar.setText("")
        self.gui.x_data_searchbar.setText("")

        self.data_path = self.bare_data_path + "\\" + year + "\\" + month + "\\" + day

        if os.path.isdir(self.data_path):
            self.update_data_list()
        else:
            self.gui.y_data.clear()
            self.gui.x_data.clear()

    def match_data_list(self):
        # new feature - if you press on x data (and check the box "Help with matching y data"), it will show you only the related y data:
        try:
            x_data_name = self.gui.x_data.currentItem().text()
            self.log.info(f"x_data_name was pressed!")
            pattern = r'_x(?=_\d{2}_\d{2}_\d{2}$)'
            match = re.search(pattern, x_data_name)
            self.log.info(f"x data = {x_data_name}, match = {match}")
            if match:
                extracted_x = match.group()
                modified_string = re.sub(pattern, '', x_data_name) # without _x_
                self.gui.y_data.clear() # don't care about the y search anymore
                # self.gui.y_data.addItem(modified_string) # check the filename here

                # add all the y data with a variance of a minute:
                modified_string_var = modified_string[:-4]
                self.gui.warning_msg.setText(f"Good! x_data = {x_data_name} search all y data that starts with {modified_string_var}")

                for filename in os.listdir(self.data_path):
                    if filename.endswith('.txt') and modified_string_var in filename:
                        self.gui.y_data.addItem(filename[:-4])
            else:
                self.gui.warning_msg.setText(f"If you want y matching, please select a file with _x_ in its name")
        except:
            self.gui.warning_msg.setText("WARNING: no x-data selected. First select and then press help matching again.")

    def update_data_list(self):
        """ Updates list of x and y data """

        self.gui.y_data.clear()
        self.gui.x_data.clear()

        x_search = self.gui.x_data_searchbar.text()
        y_search = self.gui.y_data_searchbar.text()

        for filename in os.listdir(self.data_path):
            if filename.endswith('.txt'):
                if x_search == "":
                    self.gui.x_data.addItem(filename[:-4])
                else:
                    if x_search in filename:
                        self.log.info(f"searching for {filename[:-4]}")
                        self.gui.x_data.addItem(filename[:-4])

                if y_search == "":
                    self.gui.y_data.addItem(filename[:-4])
                else:
                    if y_search in filename:
                        self.gui.y_data.addItem(filename[:-4])

    def update_fit_method(self):
        """ updates the function used for fitting """

        fit_method = self.gui.fit_method.currentItem().text()

        if fit_method == "Single Gaussian":
            self.gui.fit_param.setText("freq,amplitude,width,offset")
            self.gui.p0_val.setText("freq,amplitude,width,offset")
            self.fitting_f = single_gaussian

        if fit_method == "Double Gaussian":
            self.gui.fit_param.setText("freq1,amplitude1,freq2,amplitude2,width,offset")
            self.gui.p0_val.setText("freq1,amplitude1,freq2,amplitude2,width,offset")
            self.fitting_f = double_gaussian

        if fit_method == "Quadruple Gaussian":
            self.gui.fit_param.setText("freq1,amplitude1,freq2,amplitude2,freq3,amplitude3,freq4,amplitude4,width,offset")
            self.gui.p0_val.setText("freq1,amplitude1,freq2,amplitude2,freq3,amplitude3,freq4,amplitude4,width,offset")
            self.fitting_f = quadruple_gaussian

        if fit_method == "Sine":
            self.gui.fit_param.setText("pi_time,amplitude,offset,phase")
            self.gui.p0_val.setText("pi_time,amplitude,offset,phase")
            self.fitting_f = sine

        if fit_method == "Quartic Sine (swap-swap)":
            self.gui.fit_param.setText("pi_time,amplitude,offset")
            self.gui.p0_val.setText("pi_time,amplitude,offset")
            self.fitting_f = quartic_sine

        if fit_method == "Quadratic Decay":
            self.gui.fit_param.setText("T2,amplitde,offset")
            self.gui.p0_val.setText("T2,amplitde,offset")
            self.fitting_f = gaussian_decay

        if fit_method == "Linear Decay":
            self.gui.fit_param.setText("T2,amplitde,offset")
            self.gui.p0_val.setText("T2,amplitde,offset")
            self.fitting_f = linear_decay

        if fit_method == "Free Power Decay":
            self.gui.fit_param.setText("T2,amplitde,offset,alpha")
            self.gui.p0_val.setText("T2,amplitde,offset,alpha")
            self.fitting_f = free_power_decay

        self.use_p0 = False

    def p0_changed(self):
        self.use_p0 = True

    def plot_data(self):
        """ plots data """

        self.create_graph()

        try:
            x_data_name = self.gui.x_data.currentItem().text()
            x_data = np.loadtxt(self.data_path + "\\" + x_data_name + ".txt")
        except:
            self.gui.warning_msg.setText("WARNING: no x-data selected")
            x_data = []

        try:
            y_data_name = self.gui.y_data.currentItem().text()
            y_data = np.loadtxt(self.data_path + "\\" + y_data_name + ".txt")
        except:
            self.gui.warning_msg.setText("WARNING: no y-data selected")
            y_data = []

        thrsh = self.gui.thrsh_val.value()

        plot_method = self.gui.plot_method.currentItem().text()

        if plot_method is None:
            plot_method = "Standard 1D plot (no x-axis)"

        if plot_method == "Standard 1D plot (no x-axis)":
            x, y = self.plot_1D(x_data, y_data, x_axis=False)

        if plot_method == "Standard 1D plot":
            x, y = self.plot_1D(x_data, y_data, x_axis=True)

        if plot_method == "Thresholded 1D plot (no x-axis)":
            x, y = self.plot_1D_thrsh(x_data, y_data, thrsh=thrsh, x_axis=False)

        if plot_method == "Thresholded 1D plot":
            x, y = self.plot_1D_thrsh(x_data, y_data, thrsh=thrsh, x_axis=True)

        if plot_method == "Histogram":
            x, y = self.plot_hist(y_data, thrsh=thrsh)

        if self.gui.fit_check.isChecked() and self.fitting_f is not None:
            self.fit_and_plot(x, y)

    def plot_1D(self, x=None, y=None, x_axis=False):
        """ Straightforward 1D plot of data """

        self.choose_color_index()

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                self.current_color_index
            ],
                width=2)
        )

        # checks if data is y data is 2-dimensional and if so, averages it to a 1-D vector
        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y, axis=0)
        else:
            data = y

        if x_axis:
            if len(x) == len(data):
                self.curve.setData(x, data)
            else:
                self.gui.warning_msg.setText("WARNING: x-data and y-data not same length")
        else:
            self.curve.setData(data)

        return x, data

    def plot_1D_thrsh(self, x=None, y=None, thrsh=0, x_axis=False):
        """ Thresholded 1D plot of data """
        self.choose_color_index()

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                self.current_color_index
            ],
                width=2)
        )

        # checks if data is y data is 2-dimensional and if so, averages it to a 1-D vector
        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y > thrsh, axis=0)
        else:
            data = 1 * (y > thrsh)

        if x_axis:
            if len(x) == len(data):
                self.curve.setData(x, data)
            else:
                self.gui.warning_msg.setText("WARNING: x-data and y-data not same length")
        else:
            self.curve.setData(data)

        return x, data

    def plot_hist(self, y=None, thrsh=0):
        """ Occurence histogram of data (integer bins) """

        self.choose_color_index()
        self.curve_l = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(self.gui.COLOR_LIST[self.current_color_index]), width=0.5)

        self.choose_color_index()
        self.curve_h = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(self.gui.COLOR_LIST[self.current_color_index]), width=0.5)

        self.graph.addItem(self.curve_l)
        self.graph.addItem(self.curve_h)

        BIN_NUMS = int(np.round(np.max(y)) + 1)

        data, _ = np.histogram(y.flatten(), bins=BIN_NUMS, range=(0, BIN_NUMS - 1))

        x = np.arange(0, len(data))
        self.curve_l.setOpts(x=x, height=(x <= thrsh) * data, width=0.5)
        self.curve_h.setOpts(x=x, height=(x > thrsh) * data, width=0.5)

        return x, y

    def fit_and_plot(self, x, y):
        """ fits given data, plots it, and displays optimized fitting parameters """

        if self.use_p0:
            p0_str = self.gui.p0_val.text()
            p0 = [float(entry) for entry in p0_str.split(',')]

            popt, _ = curve_fit(self.fitting_f, x, y, p0=p0)
        else:
            popt, _ = curve_fit(self.fitting_f, x, y)

        x_fit = np.linspace(np.min(x), np.max(x), 1000)
        self.plot_1D(x=x_fit, y=self.fitting_f(x_fit, *popt), x_axis=True)

        popt_string = ""
        for i in range(len(popt)):
            popt_string += f"{popt[i]:.4e}" + ","
        popt_string = popt_string[:-1]
        self.gui.p0_val.setText(popt_string)

    def choose_color_index(self):
        """ Updates color index for plotting """
        self.current_color_index += 1
        if self.current_color_index > (len(self.gui.COLOR_LIST) - 1):
            self.current_color_index = 0

    def create_graph(self):
        """ Creates graph to plot on if it does not exist"""

        if self.graph is None:
            self.graph = self.gui.add_graph()

    def clear_all_data(self):
        """ clears all plots """
        for index in reversed(range(self.gui.graph_layout.count())):
            try:
                self.gui.graph_layout.itemAt(index).widget().deleteLater()
            except AttributeError:
                try:
                    self.gui.graph_layout.itemAt(index).layout().deleteLater()
                except AttributeError:
                    pass
        self.gui.windows = {}
        self.graph = None


def main():
    control = GalvoScan()
    control.gui.app.exec_()


def launch(**kwargs):

    config = load_script_config(
        script='galvo_scan',
        config=kwargs['config'],
        logger=kwargs['logger']
    )

    # Instantiate Monitor script
    control = GalvoScan(
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
