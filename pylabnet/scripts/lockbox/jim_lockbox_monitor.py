from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (unpack_launcher, create_server,
                                           load_config, get_gui_widgets, get_legend_from_graphics_view, add_to_legend, find_client,
                                           load_script_config, get_ip)
from pylabnet.utils.logging.logger import LogClient, LogHandler

import time
import numpy as np
import pyqtgraph as pg


class JimLockboxGUI:

    def __init__(self, lockbox_client, logger_client, gui='lockbox', server_port=None):

        self.log = LogHandler(logger_client)
        self.lockbox = lockbox_client

        # Instantiate gui
        self.gui = Window(
            gui_template=gui,
            host=get_ip(),
            port=server_port,
            log=self.log
        )

        self.gui.apply_stylesheet()
        self.initialize_buttons()
        self.initialize_fields()

        # Configure plots
        # Get actual legend widgets
        # self.widgets['legend'] = [get_legend_from_graphics_view(legend) for legend in self.widgets['legend']]
        # self.widgets['curve'] = []

    def run(self):
        """ Runs the lockbox infinitely """

        tic = time.time()

        # Continuously update data per read time
        while True:
            if (time.time() - tic) > self.read_time:
                self.update_status()
                tic = time.time()

            self.gui.force_update()

    def initialize_buttons(self):
        self.gui.set_P.clicked.connect(
            lambda: self.lockbox.set_P(float(self.gui.input_P.value()))
        )
        self.gui.set_I.clicked.connect(
            lambda: self.lockbox.set_I(float(self.gui.input_I.value()))
        )
        self.gui.set_D.clicked.connect(
            lambda: self.lockbox.set_D(float(self.gui.input_D.value()))
        )
        self.gui.set_int_time.clicked.connect(
            lambda: self.lockbox.set_int_time(float(self.gui.input_int_time.value()))
        )
        self.gui.set_offset.clicked.connect(
            lambda: self.lockbox.set_offset(float(self.gui.input_offset.value()))
        )
        self.gui.reset.clicked.connect(
            lambda: self.lockbox.reset()
        )
        self.gui.set_read.clicked.connect(
            lambda: setattr(self, "read_time", float(self.gui.input_read.value()))
        )

    def initialize_fields(self):
        self.update_status()

        self.gui.input_P.setValue(self.search_field(self.status, "PVal"))
        self.gui.input_I.setValue(self.search_field(self.status, "IVal"))
        self.gui.input_D.setValue(self.search_field(self.status, "DVal"))
        self.gui.input_int_time.setValue(self.search_field(self.status, "Timebase"))
        self.gui.input_offset.setValue(self.search_field(self.status, "Offset"))

        self.read_time = float(self.gui.input_read.value())

    def update_status(self):
        self.status = self.lockbox.get_status()
        self.gui.statusText.setValue(self.status)
        self.update_value_labels()

    def update_value_labels(self):
        self.gui.val_P.setValue(self.search_field(self.status, "PVal"))
        self.gui.val_I.setValue(self.search_field(self.status, "IVal"))
        self.gui.val_D.setValue(self.search_field(self.status, "DVal"))
        self.gui.val_int_time.setValue(self.search_field(self.status, "Timebase"))
        self.gui.val_offset.setValue(self.search_field(self.status, "Offset"))
        self.gui.val_PIDout.setValue(self.search_field(self.status, "PIDOut"))

    # Technical methods

    def _initialize_channel(self, index, channel):

        # Get wavelength and initialize data arrays
        channel.initialize(
            wavelength=self.wlm_client.get_wavelength(channel.number),
            display_pts=self.display_pts
        )

        # Create curves
        # frequency
        self.widgets['curve'].append(self.widgets['graph'][2 * index].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        ))
        add_to_legend(
            legend=self.widgets['legend'][2 * index],
            curve=self.widgets['curve'][4 * index],
            curve_name=channel.curve_name
        )

        # Setpoint
        self.widgets['curve'].append(self.widgets['graph'][2 * index].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
        ))
        add_to_legend(
            legend=self.widgets['legend'][2 * index],
            curve=self.widgets['curve'][4 * index + 1],
            curve_name=channel.setpoint_name
        )

        # Clear data
        self.widgets['clear'][2 * index].clicked.connect(
            lambda: self.clear_channel(channel)
        )

        # Setpoint reset
        self.widgets['rs'][index].clicked.connect(
            lambda: self.update_parameters(dict(
                channel=channel.number,
                setpoint=channel.data[-1]
            ))
        )

        # Voltage
        self.widgets['curve'].append(self.widgets['graph'][2 * index + 1].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        ))
        add_to_legend(
            legend=self.widgets['legend'][2 * index + 1],
            curve=self.widgets['curve'][4 * index + 2],
            curve_name=channel.voltage_curve
        )

        # Error
        self.widgets['curve'].append(self.widgets['graph'][2 * index + 1].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
        ))
        add_to_legend(
            legend=self.widgets['legend'][2 * index + 1],
            curve=self.widgets['curve'][4 * index + 3],
            curve_name=channel.error_curve
        )

        # zero
        self.widgets['zero'][2 * index].clicked.connect(
            lambda: self.zero_voltage(channel)
        )
        self.widgets['zero'][2 * index + 1].clicked.connect(
            lambda: self.zero_voltage(channel)
        )

    def _update_channels(self):
        """ Updates all channels + displays

        Called continuously inside run() method to refresh WLM data and output on GUI
        """

        for index, channel in enumerate(self.channels):

            # Check for override
            if channel.setpoint_override:
                self.widgets['sp'][index].setValue(channel.setpoint_override)
                channel.setpoint_override = 0

            # Update data with the new wavelength
            channel.update(self.wlm_client.get_wavelength(channel.number))

            # Update frequency
            self.widgets['curve'][4 * index].setData(channel.data)
            self.widgets['freq'][index].setValue(channel.data[-1])

            # Update setpoints
            self.widgets['curve'][4 * index + 1].setData(channel.sp_data)

            # Set the error boolean (true if the lock is active and we are outside the error threshold)
            if channel.lock and np.abs(channel.data[-1] - channel.setpoint) > self.threshold:
                self.widgets['error_status'][index].setChecked(True)
            else:
                self.widgets['error_status'][index].setChecked(False)

            # Now update lock + voltage plots
            self.widgets['curve'][4 * index + 2].setData(channel.voltage)
            self.widgets['voltage'][index].setValue(channel.voltage[-1])


def launch(**kwargs):
    """ Launches the count monitor script """

    logger, clients = kwargs['logger'], kwargs['clients']

    config = load_script_config(
        script='jim_lockbox_monitor',
        config=kwargs['config'],
        logger=logger
    )

    lockbox_client = find_client(
        clients,
        config,
        client_type='jim_lockbox',
        client_config='goldberry',
        logger=logger
    )

    jim_lockbox_gui = JimLockboxGUI(
        lockbox_client=lockbox_client,
        logger_client=logger,
        server_port=kwargs['server_port']
    )

    jim_lockbox_gui.run()
