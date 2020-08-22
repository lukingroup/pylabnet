import numpy as np
import time

from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, generate_widgets, load_config
from pylabnet.network.client_server import smaract_mcs2


class Controller:
    """ A script class for controlling MCS2 positioners + interfacing with GUI"""

    NUM_CHANNELS = 9
    WIDGET_DICT = dict(
        step_left=NUM_CHANNELS, step_right=NUM_CHANNELS, walk_left=NUM_CHANNELS,
        walk_right=NUM_CHANNELS, n_steps=NUM_CHANNELS, is_moving=NUM_CHANNELS,
        amplitude=NUM_CHANNELS, frequency=NUM_CHANNELS, velocity=NUM_CHANNELS, voltage=NUM_CHANNELS,
        lock_button=int(NUM_CHANNELS/3)
    )
    DC_TOLERANCE = 0.1
    AXIS_ORDER = [[4, 3, 7], [6, 1, 5], [8, 0, 2]]

    def __init__(self, nanopos_client: smaract_mcs2.Client , gui_client, log_client=None, config=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui_client: (pylabnet.network.client_server.external_gui.Client)
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        :param config: (str) name of config file, optional
        """

        self.pos = nanopos_client
        self.log = LogHandler(logger=log_client)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)

        # Unpack all widgets
        (self.step_left, self.step_right, self.walk_left, self.walk_right,
         self.n_steps, self.is_moving, self.amplitude, self.frequency,
         self.velocity, self.voltage, self.lock_button) = generate_widgets(self.WIDGET_DICT)

        # Additional attributes
        self.prev_amplitude = [50]*self.NUM_CHANNELS
        self.prev_frequency = [30]*self.NUM_CHANNELS
        self.prev_velocity = [100]*self.NUM_CHANNELS
        self.prev_voltage = [50]*self.NUM_CHANNELS
        self.voltage_override = False
        self.config=config
        self.lock_status = [False]*int(self.NUM_CHANNELS/3)

    def initialize_gui(self):
        """ Initializes the GUI (assigns channels)"""

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            self._initialize_channel(channel_index)

        # Handle global GUI stuff
        self.gui.assign_event_button(
            event_widget='load_button', event_label='load_button'
        )
        self.gui.assign_event_button(
            event_widget='save_button', event_label='save_button'
        )
        self.gui.assign_label(
            label_widget='config_label', label_label='config_label'
        )
        self.gui.set_label(
            self.config, 'config_label'
        )

        # Lock buttons
        for lock_button in self.lock_button:
            self.gui.assign_event_button(
                event_widget=lock_button, event_label=lock_button
            )

    def initialize_parameters(self, channel, params):
        """ Initializes all parameters to values given by params, except for DC voltage

        :param channel: (int) channel index (from 0)
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        """

        self.pos.set_parameters(channel, amplitude=params[2])
        self.pos.set_parameters(channel, frequency=params[3])
        self.pos.set_parameters(channel, dc_vel=params[4])

        # Measure DC voltage and set it in the GUI
        self._set_voltage_display(channel)

    def run(self):
        """ Runs the Positioner control (takes any necessary action) """

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            # Check for lock events
            locked = self._handle_lock(channel_index)

            # Get GUI values
            params = self.get_GUI_parameters(channel_index)

            # Update current status on GUI
            self._update_channel(channel_index, params)

            # Handle parameter updates
            self._update_parameters(channel_index, params)

            # Handle DC change
            # this line of code was throwing an error (params[5] comes up None), so we handle it here
            voltage_failure = False
            try:
                if np.abs(params[5]-self.prev_voltage[channel_index]) > self.DC_TOLERANCE and not locked:
                    self.pos.set_voltage(channel_index, params[5])
            except Exception as e:
                voltage_failure = True
                self.log.warn(f'{e}, failed to check DC voltage change for channel {channel_index}')

            # Handle a step event
            if self.gui.was_button_pressed(self.step_left[channel_index]) and not locked:
                self.gui.change_button_background_color(self.step_left[channel_index], color='red')
                self.pos.n_steps(channel_index, n=-params[0])
                time.sleep(0.15)
                self.gui.change_button_background_color(self.step_left[channel_index], color='black')
                self._set_voltage_display(channel_index)
            if self.gui.was_button_pressed(self.step_right[channel_index]) and not locked:
                self.gui.change_button_background_color(self.step_right[channel_index], color='red')
                self.pos.n_steps(channel_index, n=params[0])
                time.sleep(0.15)
                self.gui.change_button_background_color(self.step_right[channel_index], color='black')
                self._set_voltage_display(channel_index)

            # Handle walk event
            walker = self.walk_left[channel_index]
            if self.gui.was_button_pressed(walker) and not locked:
                self._walk(channel_index, walker, params, left=True)
            walker = self.walk_right[channel_index]
            if self.gui.was_button_pressed(walker) and not locked:
                self._walk(channel_index,walker, params, left=False)

            # Handle GUI Saving and Loading
            self._load_save_settings()

            # Update the previous values for future use
            (
                self.prev_amplitude[channel_index],
                self.prev_frequency[channel_index],
                self.prev_velocity[channel_index]
            ) = params[2], params[3], params[4]

            # If we want to override the previous DC voltage reading
            if not self.voltage_override and not voltage_failure:
                self.prev_voltage[channel_index] = params[5]
            else:
                self.voltage_override = False

            if self.gui.was_button_pressed('emergency_button'):
                self.stop_all()

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

    def stop_all(self):
        """ Stops all channels """

        for channel in range(self.NUM_CHANNELS):
            self.pos.stop(channel)

    def load_settings(self):
        """ Loads settings from configuration """
        self.gui.load_gui(
                self.gui.get_text('config_label'),
                logger=self.log
            )

    # Technical methods

    def _set_voltage_display(self, channel):
        """ Sets the voltage on the GUI to the current value measured by the controller

        :param channel: (int) channel index (from 0)
        """

        voltage = self.pos.get_voltage(channel)
        self.prev_voltage[channel] = voltage
        self.gui.activate_scalar(self.voltage[channel])
        self.gui.set_scalar(voltage, self.voltage[channel])
        self.voltage_override = True

        # Give some time for GUI updating
        time.sleep(0.05)
        self.gui.deactivate_scalar(self.voltage[channel])

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
            event_widget=self.walk_right[index], event_label=self.walk_right[index]
        )
        self.gui.assign_event_button(
            event_widget='emergency_button', event_label='emergency_button'
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
            if not params[1]:
                self.gui.set_scalar(True, self.is_moving[channel])
        else:
            if params[1]:
                self.gui.set_scalar(False, self.is_moving[channel])

    def _update_parameters(self, channel, params):
        """ Updates current parameters on device

        :param channel: (int) channel index (from 0)
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        """

        if params[2] != self.prev_amplitude[channel]:
            self.pos.set_parameters(channel, amplitude=params[2])
        if params[3] != self.prev_frequency[channel]:
            self.pos.set_parameters(channel, frequency=params[3])
        if params[4] != self.prev_velocity[channel]:
            self.pos.set_parameters(channel, dc_vel=params[4])

    def _walk(self, channel, walker, params, left=False):
        """ Performs a walk until the button is released

        :param channel: (int) channel index (from 0)
        :param walker: (str) event button label of walk button
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity,
            voltage
        :param left: (bool) whether or not to walk left
        """

        walking = True
        self.gui.change_button_background_color(walker, 'red')
        while walking:

            # Check for button release
            if self.gui.was_button_released(walker):
                self.stop_all()
                self.gui.set_scalar(False, self.is_moving[channel])
                self.gui.change_button_background_color(walker, 'black')
                time.sleep(0.05)
                self._set_voltage_display(channel)
                walking = False

                # Reset all walk buttons so no steps are taken anymore
                for button in self.walk_left:
                    self.gui.reset_button(button)
                for button in self.walk_right:
                    self.gui.reset_button(button)
            else:

                # Update channel and move
                self._update_channel(channel, params)
                if not self.gui.get_scalar(self.is_moving[channel]):
                    self.pos.move(channel, backward=left)

            if self.gui.was_button_pressed('emergency_button'):
                self.stop_all()
                walking = False

    def _load_save_settings(self):
        """Saves or loads settings if relevant"""

        if self.gui.was_button_pressed('load_button'):
            self.load_settings()
        if self.gui.was_button_pressed('save_button'):
            scalars = self.n_steps + self.amplitude + self.frequency + self.velocity
            self.gui.save_gui(
                self.gui.get_text('config_label'),
                logger=self.log,
                scalars=scalars
            )

    def _handle_lock(self, current_channel):
        """ Checks whether any channels were locked and applies/removes lock

        :param current_channel: (int) current channel index
        """

        locked = False
        for index, lock_button in enumerate(self.lock_button):
            if self.gui.was_button_pressed(lock_button):

                # Check if the stack was already locked, then unlock, else lock
                if self.lock_status[index]:
                    self.lock_status[index] = False
                    self.gui.change_button_background_color(lock_button, 'rgb(100, 0, 0)')
                    self.gui.set_button_text(lock_button, 'Lock')
                else:
                    self.lock_status[index] = True
                    self.gui.change_button_background_color(lock_button, 'rgb(0, 100, 0)')
                    self.gui.set_button_text(lock_button, 'Unlock')

            # Check if the current channel corresponds to this lock button and apply
            if current_channel in self.AXIS_ORDER[index]:
                locked = self.lock_status[index]

        return locked


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    nanopos_client = clients['mcs2']
    gui_client = guis['positioner_control']

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger, config=kwargs['config'])

    # Initialize all GUI channels
    control.initialize_gui()
    # Initialize parameters
    for channel_index in range(control.NUM_CHANNELS):
        params = control.get_GUI_parameters(channel_index)
        control.initialize_parameters(channel_index, params)

    try:
        control.load_settings()
    except Exception as e:
        logger.warn(e)
        logger.warn('Failed to load settings from config file')

    while True:

        if not control.gui.is_paused:
            control.run()
            pass

    # Mitigate warnings about unused variables
    if loghost and logport and params:
        pass
