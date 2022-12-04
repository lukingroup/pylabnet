from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (unpack_launcher, create_server,
                                           load_config, get_gui_widgets, get_legend_from_graphics_view, add_to_legend, find_client,
                                           load_script_config, get_ip)
from pylabnet.utils.logging.logger import LogClient, LogHandler

import re
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

        self.display_pts = 1000
        self.PID_out_arr = None
        self.graph = self.gui.output_plot
        self.curve = self.graph.plot(pen=pg.mkPen(color=self.gui.COLOR_LIST[0]))

        self.gui.apply_stylesheet()

        # Set the button functions
        self.initialize_buttons()

        # Read initial status and populate fields with current values
        self.initialize_fields()

        # Configure plots
        # Get actual legend widgets

        # self.widgets['legend'] = [get_legend_from_graphics_view(legend) for legend in self.widgets['legend']]
        # add_to_legend(
        #     legend=self.widgets['legend'][2 * index],
        #     curve=self.curve,
        #     curve_name=channel.curve_name
        # )

    def run(self):
        """ Runs the lockbox infinitely, updating every read_time seconds. """
        tic = time.time()

        # Continuously update data per read time
        while True:
            if (time.time() - tic) > self.read_time:
                self.update_status()
                tic = time.time()
            self.gui.force_update()

    def initialize_buttons(self):
        """ Connect the buttons to their functions. """

        self.gui.set_P.clicked.connect(
            lambda: self.lockbox.set_P(self.gui.input_P.value())
        )
        self.gui.set_I.clicked.connect(
            lambda: self.lockbox.set_I(self.gui.input_I.value())
        )
        self.gui.set_D.clicked.connect(
            lambda: self.lockbox.set_D(self.gui.input_D.value())
        )
        self.gui.set_int_time.clicked.connect(
            lambda: self.lockbox.set_int_time(self.gui.input_int_time.value())
        )
        self.gui.set_offset.clicked.connect(
            lambda: self.lockbox.set_offset(self.gui.input_offset.value())
        )
        self.gui.reset.clicked.connect(
            lambda: self.lockbox.reset()
        )
        self.gui.set_read.clicked.connect(
            lambda: setattr(self, "read_time", self.gui.input_read.value())
        )

    def initialize_fields(self):
        self.update_status()

        # Only update the input fields at initialization time
        self.gui.input_P.setValue(self.search_field(self.status, "PVal"))
        self.gui.input_I.setValue(self.search_field(self.status, "IVal"))
        self.gui.input_D.setValue(self.search_field(self.status, "DVal"))
        self.gui.input_int_time.setValue(self.search_field(self.status, "Timebase"))
        self.gui.input_offset.setValue(self.search_field(self.status, "Offset"))

        self.read_time = self.gui.input_read.value()

    def update_status(self):
        """ Read current status from the lockbox, then update the full status dump box
            as well as the individual parameters labels and plot. """
        self.status = self.lockbox.get_status()
        self.gui.statusText.setText(self.status)
        self.update_value_labels()
        self.update_plot()

    def update_value_labels(self):
        new_PIDOut = self.search_field(self.status, "PIDOut")

        self.gui.val_P.setText(str(self.search_field(self.status, "PVal")))
        self.gui.val_I.setText(str(self.search_field(self.status, "IVal")))
        self.gui.val_D.setText(str(self.search_field(self.status, "DVal")))
        self.gui.val_int_time.setText(str(self.search_field(self.status, "Timebase")))
        self.gui.val_offset.setText(str(self.search_field(self.status, "Offset")))
        self.gui.val_PIDout.setText(str(new_PIDOut))

        if self.PID_out_arr is None:
            self.PID_out_arr = new_PIDOut * np.ones(self.display_pts)
        else:
            self.PID_out_arr = np.append(self.PID_out_arr[1:], new_PIDOut)
        self.curve.setData(self.PID_out_arr)

    def search_field(self, string, field):
        """ Searches for a field of the format [FIELD] = xxxxxx
        where the xxx are float numbers, and returns the extract numbers.

        :param msg: (str) message to be sent
        """
        valid_fields = ["dCount1", "Count2", "Timebase", "PVal", "IVal", "DVal", "ErrorVal", "Integrator", "Offset", "PIDOut"]

        if field not in valid_fields:
            raise ValueError("Invalid Lockbox field.")

        regex_search = re.search(f"{field} = ([0-9\.]*)", string)

        # Check if field is not contained in string
        if regex_search is not None:
            return float(regex_search.group(1))
        else:
            return ""


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
