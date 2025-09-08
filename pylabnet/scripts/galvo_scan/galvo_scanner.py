""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from scipy.optimize import curve_fit
import time

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets


REFRESH_TIME = 10  # refresh rate in ms, try increasing if GUI lags

NIDAQ_SAMPLING_RATE = 5 # in kHz
WAVEFUNC_LEN = 2000 # in ms


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
        self.scanning = False

        # Find the client
        device_config = None
        for server in self.config['servers']:
            # Currently works for nidaqmx only, but could be generalized to other daq types
            if server['type'] == 'nidaqmx':
                device_type = server['type']
                device_config = server['config']
                break
        try:
            self.daq_client = find_client(client_tuples, self.config, device_type, device_config, self.log)

            if (self.daq_client == None):
                device_item = QtWidgets.QListWidgetItem(f"{device_type}_{device_config}")
                device_item.setForeground(Qt.gray)
                self.gui.clients.addItem(device_item)
                self.log.error("Datataker missing client: " + device_type)
            else:
                device_item = QtWidgets.QListWidgetItem(f"{device_type}_{device_config}")
                device_item.setToolTip(str(device_config))
                self.gui.clients.addItem(device_item)

        except NameError:
            self.log.error('No daq device identified in script config file')

        # Configure button clicks
        self.gui.configure.clicked.connect(self.configure)

        self.gui.wavelist_x.itemClicked.connect(self.update_wavetype_x)
        self.gui.wavelist_y.itemClicked.connect(self.update_wavetype_y)

        self.gui.start.clicked.connect(self.start_stop_galvo)

        #self.gui.showMaximized()
        self.gui.apply_stylesheet()

        self.run()

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
            self.scanning = True
            self.log.info('Galvo started')

        else:
            self.gui.start.setStyleSheet('background-color: green')
            self.gui.start.setText('Start Galvo')
            self.scanning = False
            self.log.info('Galvo stopped')

    def run(self):
        # Continuously update data until paused
        self.running = True

        while self.running:
            time.sleep(REFRESH_TIME / 1000)
            self._update_output()
            self.gui.force_update()

    def _update_output(self):

        if self.scanning == False:
            return
        else:
            self.daq_client.set_ao_voltage([self.daq_x, self.daq_y], [self.wavefunction_x, self.wavefunction_y])


def build_wavefunction(wavetype, period, dc, amp, offset):
    """ builds wavefuncions for galvo scan """

    x = np.linspace(0, WAVEFUNC_LEN - 1, WAVEFUNC_LEN * NIDAQ_SAMPLING_RATE)

    if wavetype == "Sine wave":
        return (sine(x, period, amp, offset)).tolist()

    if wavetype == "Square wave":
        return (square_wave(x, period, dc, amp, offset)).tolist()

    if wavetype == "Triangle wave":
        return (triangle_wave(x, period, amp, offset)).tolist()

    if wavetype == "Sawtooth wave":
        return (sawtooth_wave(x, period, amp, offset)).tolist()


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
