""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import os
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from scipy.optimize import curve_fit
from lmfit import Model
from lmfit import Parameter, Parameters
import lmfit
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets
import re
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton

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
        # self.gui.p0_val.textChanged.connect(self.p0_changed)

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
                modified_string = re.sub(
                    pattern, '', x_data_name)  # without _x_
                self.gui.y_data.clear()  # don't care about the y search anymore
                # self.gui.y_data.addItem(modified_string) # check the filename here

                # add all the y data with a variance of a minute:
                modified_string_var = modified_string[:-4]
                self.gui.warning_msg.setText(
                    f"Good! x_data = {x_data_name} search all y data that starts with {modified_string_var}")

                for filename in os.listdir(self.data_path):
                    if filename.endswith('.txt') and modified_string_var in filename:
                        self.gui.y_data.addItem(filename[:-4])
            else:
                self.gui.warning_msg.setText(
                    f"If you want y matching, please select a file with _x_ in its name")
        except:
            self.gui.warning_msg.setText(
                "WARNING: no x-data selected. First select and then press help matching again.")

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

####################### param_dict and input p0 scroll area ######################

    def create_gridlayout(self):

        fit_scrollarea = self.gui.fit_scrollarea

        self.gui.fit_scrollAreaWidgetContents = QtWidgets.QWidget()
        self.gui.fit_dict_gridlayout = QtWidgets.QGridLayout(
            self.gui.fit_scrollAreaWidgetContents)
        fit_scrollarea.setWidget(self.gui.fit_scrollAreaWidgetContents)

    def update_p0_form(self):

        self.create_gridlayout()

        # Build fit dict modification form
        fit_grid_layout = self.gui.fit_dict_gridlayout

        if not self.valid_fit_dict:
            label = QLabel("No FIT_DICT found.")
            fit_grid_layout.addWidget(label, 0, 0)
        else:
            try:
                for i, (variable_name, entry_dict) in enumerate(self.fit_dict.items()):
                    variable = QLabel(str(variable_name))
                    fit_grid_layout.addWidget(variable, i, 0)

                    for j, (labelname, default_value) in enumerate(entry_dict.items()):
                        label = QLabel(str(labelname))
                        value_entry = QLineEdit(str(default_value))
                        fit_grid_layout.addWidget(label, i, 1 + 2 * j)
                        fit_grid_layout.addWidget(value_entry, i, 1 + 2 * j + 1)

            except AttributeError:
                label = QLabel("fit_DICT found, but structure not valid.")
                fit_grid_layout.addWidget(label, 0, 0)
                self.valid_fit_dict = False


##################### fitting methods ############

    def update_fit_method(self):
        """ updates the function used for fitting """

        fit_method = self.gui.fit_method.currentItem().text()

        if fit_method == "Single Gaussian":
            self.gui.fit_param.setText("freq,amplitude,width,offset")
            self.fitting_f = single_gaussian
            self.valid_fit_dict = True

            self.fit_dict = {
                'freq': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude': {'p0': 0, 'vary': 1, 'result': -1},
                'width': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }

            self.update_p0_form()

        if fit_method == "Double Gaussian":
            self.gui.fit_param.setText(
                "freq1,amplitude1,freq2,amplitude2,width,offset")
            self.fitting_f = double_gaussian
            self.valid_fit_dict = True

            self.fit_dict = {
                'freq1': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude1': {'p0': 0, 'vary': 1, 'result': -1},
                'freq2': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude2': {'p0': 0, 'vary': 1, 'result': -1},
                'width': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }

            self.update_p0_form()

        if fit_method == "Quadruple Gaussian":
            self.gui.fit_param.setText(
                "freq1,amplitude1,freq2,amplitude2,freq3,amplitude3,freq4,amplitude4,width,offset")
            self.fitting_f = quadruple_gaussian
            self.valid_fit_dict = True
            self.fit_dict = {
                'freq1': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude1': {'p0': 0, 'vary': 1, 'result': -1},
                'freq2': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude2': {'p0': 0, 'vary': 1, 'result': -1},
                'freq3': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude3': {'p0': 0, 'vary': 1, 'result': -1},
                'freq4': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude4': {'p0': 0, 'vary': 1, 'result': -1},
                'width': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "Sine":
            self.gui.fit_param.setText("pi_time,amplitude,offset,phase")
            self.fitting_f = sine
            self.valid_fit_dict = True
            self.fit_dict = {
                'pi_time': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
                'phase': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "Quartic Sine (swap-swap)":
            self.gui.fit_param.setText("pi_time,amplitude,offset")
            self.fitting_f = quartic_sine
            self.valid_fit_dict = True
            self.fit_dict = {
                'pi_time': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitude': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "Quadratic Decay":
            self.gui.fit_param.setText("T2,amplitde,offset")
            self.fitting_f = gaussian_decay
            self.valid_fit_dict = True
            self.fit_dict = {
                'T2': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitde': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "Linear Decay":
            self.gui.fit_param.setText("T2,amplitde,offset")
            self.fitting_f = linear_decay
            self.valid_fit_dict = True
            self.fit_dict = {
                'T2': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitde': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "Free Power Decay":
            self.gui.fit_param.setText("T2,amplitde,offset,alpha")
            self.fitting_f = free_power_decay
            self.valid_fit_dict = True
            self.fit_dict = {
                'T2': {'p0': 0, 'vary': 1, 'result': -1},
                'amplitde': {'p0': 0, 'vary': 1, 'result': -1},
                'offset': {'p0': 0, 'vary': 1, 'result': -1},
                'alpha': {'p0': 0, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

        if fit_method == "siv cavity reflectivity":
            self.gui.fit_param.setText(
                "freq_offset_THz, freq_cavity_THz, k_Tot_GHz, offset, freq_SiV_THz, \nk_w_GHz, gamma_GHz, g_GHz, scaling_factor")

            self.fitting_f = siv_cavity_reflectivity
            self.valid_fit_dict = True
            self.fit_dict = {
                'freq_offset_THz': {'p0': 406.660, 'vary': 0, 'result': -1},
                'freq_cavity_THz': {'p0': 406.810, 'vary': 0, 'result': -1},
                'k_Tot_GHz': {'p0': 88, 'vary': 0, 'result': -1},
                'offset': {'p0': 0, 'vary': 0, 'result': -1},
                'freq_SiV_THz': {'p0': 406.660, 'vary': 1, 'result': -1},
                'k_w_GHz': {'p0': 50, 'vary': 1, 'result': -1},
                'gamma_GHz': {'p0': 0.1, 'vary': 0, 'result': -1},
                'g_GHz': {'p0': 8, 'vary': 1, 'result': -1},
                'scaling_factor': {'p0': 10, 'vary': 1, 'result': -1},
            }
            self.update_p0_form()

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
            x, y = self.plot_1D_thrsh(
                x_data, y_data, thrsh=thrsh, x_axis=False)

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
                self.gui.warning_msg.setText(
                    "WARNING: x-data and y-data not same length")
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
                self.gui.warning_msg.setText(
                    "WARNING: x-data and y-data not same length")
        else:
            self.curve.setData(data)

        return x, data

    def plot_hist(self, y=None, thrsh=0):
        """ Occurence histogram of data (integer bins) """

        self.choose_color_index()
        self.curve_l = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(
            self.gui.COLOR_LIST[self.current_color_index]), width=0.5)

        self.choose_color_index()
        self.curve_h = pg.BarGraphItem(x=[0], height=[0], brush=pg.mkBrush(
            self.gui.COLOR_LIST[self.current_color_index]), width=0.5)

        self.graph.addItem(self.curve_l)
        self.graph.addItem(self.curve_h)

        BIN_NUMS = int(np.round(np.max(y)) + 1)

        data, _ = np.histogram(y.flatten(), bins=BIN_NUMS,
                               range=(0, BIN_NUMS - 1))

        x = np.arange(0, len(data))
        self.curve_l.setOpts(x=x, height=(x <= thrsh) * data, width=0.5)
        self.curve_h.setOpts(x=x, height=(x > thrsh) * data, width=0.5)

        return x, y

    def fit_and_plot(self, x, y):
        """ Load input dict from Gridlayout in GUI"""
        """ fits given data, plots it, and displays optimized fitting parameters """

        if not self.valid_fit_dict:
            return

        # load input dict
        fit_grid_layout = self.gui.fit_dict_gridlayout
        fit_scrollarea = self.gui.fit_scrollAreaWidgetContents

        num_cols = int(fit_grid_layout.columnCount())
        num_rows = int(fit_grid_layout.rowCount())
        # omitting first one since it's the gridlayout
        fit_widgets = fit_scrollarea.children()[1:]

        params = Parameters()
        for i in range(num_rows):
            fit_param = fit_widgets[i * num_cols].text()
            fit_p0 = float(fit_widgets[i * num_cols + 2].text())
            fit_vary = float(fit_widgets[i * num_cols + 4].text())
            params.add(fit_param, value=fit_p0, vary=fit_vary)

        self.gui.warning_msg.setText(str(params))

        fit_model_func_lmfit = lmfit.Model(self.fitting_f)
        results = fit_model_func_lmfit.fit(y, params, x=x)

        x_fit = np.linspace(np.min(x), np.max(x), 1000)
        self.plot_1D(x=x_fit, y=fit_model_func_lmfit.eval(
            params=results.params, x=x_fit), x_axis=True)

        for i in range(num_rows):
            fit_param = fit_widgets[i * num_cols].text()
            fit_value_res = results.params[fit_param].value
            fit_widgets[i * num_cols + 6].setText(f"{fit_value_res:.5e}")

        ################## Show cooperativity ################
        if (self.fitting_f == siv_cavity_reflectivity):
            g = results.params['g_GHz'].value
            gamma = results.params['gamma_GHz'].value
            k_tot = results.params['k_Tot_GHz'].value
            C = 4 * g**2 / k_tot / gamma
            text_displayed_now = self.gui.fit_param.text()
            self.gui.fit_param.setText(text_displayed_now + f"; C = {C:.2e}")

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

    def reload_config(self):
        """ Loads a new config file """

        self.config = load_script_config(
            script='data_taker',
            config=self.gui.config.text(),
            logger=self.log
        )


def single_gaussian(x, freq, amplitude, width, offset):
    return amplitude * np.exp(-((x - freq) / width)**2) + offset


def double_gaussian(x, freq1, amplitude1, freq2, amplitude2, width, offset):
    return amplitude1 * np.exp(-((x - freq1) / width)**2) + \
        amplitude2 * np.exp(-((x - freq2) / width)**2) + offset


def quadruple_gaussian(x, freq1, amplitude1, freq2, amplitude2,
                       freq3, amplitude3, freq4, amplitude4, width, offset):
    return amplitude1 * np.exp(-((x - freq1) / width)**2) + \
        amplitude2 * np.exp(-((x - freq2) / width)**2) + \
        amplitude3 * np.exp(-((x - freq3) / width)**2) +\
        amplitude4 * np.exp(-((f - freq4) / width)**2) + offset


def sine(x, pi_time, amplitude, offset, phase):
    return amplitude * np.sin(np.pi / 2 * x / pi_time + np.pi / 2 * phase)**2 + offset


def quartic_sine(x, pi_time, amplitude, offset):
    return amplitude * np.sin(np.pi / 2 * x / pi_time)**4 + offset


def gaussian_decay(x, T2, amplitde, offset):
    return amplitde * np.exp(-(x / T2)**2) + offset


def linear_decay(x, T2, amplitde, offset):
    return amplitde * np.exp(-x / T2) + offset


def free_power_decay(x, T2, amplitde, offset, alpha):
    return amplitde * np.exp(-(x / T2)**alpha) + offset


def siv_cavity_reflectivity(x, freq_offset_THz, freq_SiV_THz, freq_cavity_THz, k_Tot_GHz, k_w_GHz, gamma_GHz, g_GHz, scaling_factor, offset):
    # Follow Supplementary of Erik's paper - Phys. Rev. Lett. 129, 053603. 26 July 2022
    x = x.astype(complex) * 1e-3  # now freq in GHz
    detune_a_GHz = (x + freq_offset_THz * 1e3) - freq_SiV_THz * 1e3
    detune_c_GHz = (x + freq_offset_THz * 1e3) - freq_cavity_THz * 1e3
    R = 1 - 2 * k_w_GHz / (2j * detune_c_GHz + k_Tot_GHz + 4 *
                           g_GHz**2 / (2j * detune_a_GHz + gamma_GHz))
    return scaling_factor * np.abs(R)**2 + offset


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
