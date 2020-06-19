import numpy as np

from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, generate_widgets
from pylabnet.network.client_server import smaract_mcs2


class Controller:
    """ A script class for controlling MCS2 positioners + interfacing with GUI"""

    NUM_CHANNELS = 9
    WIDGET_DICT = dict(
        step_left=NUM_CHANNELS, step_right=NUM_CHANNELS, walk_left=NUM_CHANNELS,
        walk_right=NUM_CHANNELS, n_steps=NUM_CHANNELS, is_moving=NUM_CHANNELS,
        amplitude=NUM_CHANNELS, frequency=NUM_CHANNELS, velocity=NUM_CHANNELS, voltage=NUM_CHANNELS
    )
    DC_TOLERANCE = 0.1

    def __init__(self, nanopos_client: smaract_mcs2.Client , gui_client, log_client=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui_client: (pylabnet.network.client_server.external_gui.Client)
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        """

        self.pos = nanopos_client
        self.log = LogHandler(logger=log_client)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)

        # Unpack all widgets
        (self.step_left, self.step_right, self.walk_left, self.walk_right,
         self.n_steps, self.is_moving, self.amplitude, self.frequency,
         self.velocity, self.voltage) = generate_widgets(self.WIDGET_DICT)

        # Additional attributes
        self.moving_flag = False
        self.prev_amplitude = [50]*self.NUM_CHANNELS
        self.prev_frequency = [30]*self.NUM_CHANNELS
        self.prev_velocity = [100]*self.NUM_CHANNELS
        self.prev_voltage = [50]*self.NUM_CHANNELS

    def initialize_gui(self):
        """ Initializes the GUI (assigns channels)"""

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            self._initialize_channel(channel_index)

    def run(self):
        """ Runs the Positioner control (takes any necessary action) """

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            # Get previous GUI values
            params = self.get_GUI_parameters(channel_index)

            # Update current status on GUI
            self._update_channel(channel_index, params)

            # Handle other requests assuming the positioner is not moving
            if not self.moving_flag:

                # Handle parameter updates
                self._update_parameters(channel_index, params)

                # Handle a step event
                if self.gui.was_button_pressed(self.step_left[channel_index]):
                    self.pos.n_steps(channel_index, n=-params[0])
                if self.gui.was_button_pressed(self.step_right[channel_index]):
                    self.pos.n_steps(channel_index, n=params[0])

                # Handle walk event
                walker = self.walk_left[channel_index]
                if self.gui.was_button_pressed(walker):
                    self._walk(channel_index, walker, params, left=True)
                walker = self.walk_right[channel_index]
                if self.gui.was_button_pressed(walker):
                    self._walk(channel_index,walker, params, left=False)

                # Handle DC change
                if np.abs(params[5]-self.prev_voltage[channel_index]) > self.DC_TOLERANCE:
                    self.pos.set_voltage(channel_index, params[5])


            # Update the previous values for future use
            (
                self.prev_amplitude[channel_index],
                self.prev_frequency[channel_index],
                self.prev_velocity[channel_index],
                self.prev_voltage[channel_index]
            ) = params[2], params[3], params[4], params[5]


    def get_GUI_parameters(self, channel):
        """ Gets the current GUI parameters for a given channel

        :param channel: (int) channel index (from 0)

        :return: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity, voltage
        """

        return (
            self.gui.get_scalar(self.n_steps[channel]),
            self.gui.get_scalar(self.is_moving[channel]),
            self.gui.get_scalar(self.amplitude[channel]),
            self.gui.get_scalar(self.frequency[channel]),
            self.gui.get_scalar(self.velocity[channel]),
            self.gui.get_scalar(self.voltage[channel])
        )

    # Technical methods

    def _initialize_channel(self, index):
        """ Initializes GUI for a given channel"""

        # Assign all numbers & boolean indicators
        self.gui.assign_scalar(scalar_widget=self.n_steps[index], scalar_label=self.n_steps[index])
        self.gui.assign_scalar(
            scalar_widget=self.amplitude[index], scalar_label=self.amplitude[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.frequency[index], scalar_label=self.frequency[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.velocity[index], scalar_label=self.velocity[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.voltage[index], scalar_label=self.voltage[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.is_moving[index], scalar_label=self.is_moving[index]
        )

        # Assign pushbuttons
        self.gui.assign_event_button(
            event_widget=self.step_left[index], event_label=self.step_left[index]
        )
        self.gui.assign_event_button(
            event_widget=self.step_right[index], event_label=self.step_right[index]
        )
        self.gui.assign_event_button(
            event_widget=self.walk_left[index], event_label=self.walk_left[index]
        )
        self.gui.assign_event_button(
            event_widget=self.walk_left[index], event_label=self.walk_left[index]
        )

    def _update_channel(self, channel, params):
        """ Updates current status of a channel on the GUI

        :param channel: (int) channel index (from 0)
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        """

        # Update status of positioner
        move = self.pos.is_moving(channel)
        if move:
            self.moving_flag = True
            if not params[1]:
                self.gui.set_scalar(True, self.is_moving[channel])
        else:
            self.moving_flag = False
            if params[1]:
                self.gui.set_scalar(False, self.is_moving[channel])

        # Update DC voltage
        voltage = self.pos.get_voltage(channel)
        if np.abs(voltage-params[5]) > self.DC_TOLERANCE:
            self.gui.set_scalar(self.pos.get_voltage(channel), self.voltage[channel])

    def _update_parameters(self, channel, params):
        """ Updates current parameters on device

        :param channel: (int) channel index (from 0)
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        """

        if params[2] != self.prev_amplitude:
            self.pos.set_parameters(channel, amplitude=params[2])
        if params[3] != self.prev_frequency:
            self.pos.set_parameters(channel, frequency=params[3])
        if params[4] != self.prev_velocity:
            self.pos.set_parameters(channel, velocity=params[4])

    def _walk(self, channel, walker, params, left=False):
        """ Performs a walk until the button is released

        :param channel: (int) channel index (from 0)
        :param walker: (str) event button label of walk button
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        :param left: (bool) whether or not to walk left
        """

        walking = True
        while walking:

            # Check for button release
            if self.gui.was_button_released(walker):
                self.pos.stop(channel)
                walking = False
            else:

                # Update channel and move
                self._update_channel(channel, params)
                if not self.moving_flag:
                    self.pos.move(channel, backward=left)



def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    nanopos_client = clients['smaract_mcs2']
    gui_client = guis['positioner_control']

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger)

    # Initialize all GUI channels
    control.initialize_gui()

    while True:

        if not control.gui.is_paused:
            control.run()
