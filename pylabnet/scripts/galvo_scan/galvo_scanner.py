""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from scipy.optimize import curve_fit

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets


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

        self.config = config

        self.daq_x = self.config["daq_ports"]["x_axis"]
        self.daq_y = self.config["daq_ports"]["y_axis"]

        self.configured = False
        self.wavetype_x = None
        self.wavetype_y = None

        # Configure button clicks
        self.gui.configure.clicked.connect(self.configure)

        self.gui.wavelist_x.itemClicked.connect(self.update_wavetype_x)
        self.gui.wavelist_y.itemClicked.connect(self.update_wavetype_y)

        self.gui.start.clicked.connect(self.start_stop_galvo)

        #self.gui.showMaximized()
        self.gui.apply_stylesheet()

    def configure(self):
        """ configures galvo scan wavefunctions """

        if self.wavetype_x == None:
            self.log.error("No wavefunction selected for X axis")
            return
        if self.wavetype_y == None:
            self.log.error("No wavefunction selected for Y axis")
            return

        period_x = float(self.gui.period_x.text())
        dc_x = float(self.gui.dc_x.text())
        amp_x = float(self.gui.amp_x.text())
        offset_x = float(self.gui.offset_x.text())

        period_y = float(self.gui.period_y.text())
        dc_y = float(self.gui.dc_y.text())
        amp_y = float(self.gui.amp_y.text())
        offset_y = float(self.gui.offset_y.text())

        self.wavefunction_x = build_wavefunction(self.wavetype_x, period_x, dc_x, amp_x, offset_x)
        self.wavefunction_y = build_wavefunction(self.wavetype_y, period_y, dc_y, amp_y, offset_y)

        self.log.info("Galvo scan configured!")
        self.configured = True

    def update_wavetype_x(self):
        """ updates the X axis wave type """

        self.wavetype_x = self.gui.wavelist_x.currentItem().text()

        if self.wavetype_x == "Square wave":
            self.gui.dc_x.setEnabled(True)
        else:
            self.gui.dc_x.setEnabled(False)

    def update_wavetype_y(self):
        """ updates the Y axis wave type """

        self.wavetype_y = self.gui.wavelist_y.currentItem().text()

        if self.wavetype_y == "Square wave":
            self.gui.dc_y.setEnabled(True)
        else:
            self.gui.dc_y.setEnabled(False)

    def start_stop_galvo(self):

        if self.configured == False:
            self.log.error('Configure wavefunctions before starting galvo scan!')
            return

        if self.gui.start.text() == 'Start Galvo':
            self.gui.start.setStyleSheet('background-color: red')
            self.gui.start.setText('Stop Galvo')
            self.log.info('Galvo started')

        else:
            self.gui.start.setStyleSheet('background-color: green')
            self.gui.start.setText('Start Galvo')
            self.log.info('Galvo stopped')


def build_wavefunction(wavetype, period, dc, amp, offset):
    """ builds wavefuncions for galvo scan """

    x = np.linspace(0, 1, 1000)

    if wavetype == "Sine Wave":
        return sine(x, period, amp, offset)

    if wavetype == "Square wave":
        return square_wave(x, period, dc, amp, offset)

    if wavetype == "Triangle wave":
        return triangle_wave(x, period, amp, offset)

    if wavetype == "Sawtooth wave":
        return sawtooth_wave(x, period, amp, offset)


def sine(x, period, amp, offset):
    return amp * np.sin(2 * np.pi * x / period) + offset


def square_wave(x, period, dc, amp, offset):
    return amp * (-1 / 2 + (np.mod(x / period, 1) <= (dc / 100))) + offset


def triangle_wave(x, period, amp, offset):
    return amp * (2 * np.abs(-1 / 2 + np.mod(x / period, 1)) - 1 / 2) + offset


def sawtooth_wave(x, period, amp, offset):
    return amp * (-1 / 2 + np.mod(x / period, 1)) + offset


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
