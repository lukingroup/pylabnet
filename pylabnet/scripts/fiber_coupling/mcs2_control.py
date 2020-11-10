import numpy as np
import time
import socket

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, get_gui_widgets, load_config, generate_widgets
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

    def __init__(self, nanopos_client: smaract_mcs2.Client , gui='positioner_control', log_client=None, config=None, port=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui: name of .ui file ot use
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        :param config: (str) name of config file, optional
        :param port: (int) port number for update/script server
        """

        self.pos = nanopos_client
        self.log = LogHandler(logger=log_client)
        self.gui = Window(
            gui_template=gui,
            host=socket.gethostbyname(socket.gethostname()),
            port=port
        )
        self.gui.apply_stylesheet()

        self.widgets = get_gui_widgets(**self.WIDGET_DICT)
        # Unpack all widgets
        # (self.step_left, self.step_right, self.walk_left, self.walk_right,
        #  self.n_steps, self.is_moving, self.amplitude, self.frequency,
        #  self.velocity, self.voltage, self.lock_button) = generate_widgets(self.WIDGET_DICT)
        self.save_params = generate_widgets(dict(
            n_steps=self.NUM_CHANNELS, amplitude=self.NUM_CHANNELS, frequency=self.NUM_CHANNELS, velocity=self.NUM_CHANNELS
        ))

        # Additional attributes
        self.prev_amplitude = [50]*self.NUM_CHANNELS
        self.prev_frequency = [30]*self.NUM_CHANNELS
        self.prev_velocity = [100]*self.NUM_CHANNELS
        self.prev_voltage = [50]*self.NUM_CHANNELS
        self.voltage_override = False
        self.config=config
        self.lock_status = [False]*int(self.NUM_CHANNELS/3)
        self.released = [False]*self.NUM_CHANNELS
        self.widgets['config_label'].setText(self.config)

        # Configure all button and parameter updates
        self._setup_gui()

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

    # def run(self):
    #     """ Runs the Positioner control (takes any necessary action) """

    #     # Iterate through channels
    #     for channel_index in range(self.NUM_CHANNELS):

    #         # Check for lock events
    #         locked = self._handle_lock(channel_index)

    #         # Get GUI values
    #         params = self.get_GUI_parameters(channel_index)

    #         # Update current status on GUI
    #         self._update_channel(channel_index, params)

    #         # Handle parameter updates
    #         self._update_parameters(channel_index, params)

    #         # Handle DC change
    #         # this line of code was throwing an error (params[5] comes up None), so we handle it here
    #         voltage_failure = False
    #         try:
    #             if np.abs(params[5]-self.prev_voltage[channel_index]) > self.DC_TOLERANCE and not locked:
    #                 self.pos.set_voltage(channel_index, params[5])
    #         except Exception as e:
    #             voltage_failure = True
    #             self.log.warn(f'{e}, failed to check DC voltage change for channel {channel_index}')

    #         # Handle a step event
    #         if self.gui.was_button_pressed(self.step_left[channel_index]) and not locked:
    #             self.gui.change_button_background_color(self.step_left[channel_index], color='red')
    #             self.pos.n_steps(channel_index, n=-params[0])
    #             time.sleep(0.15)
    #             self.gui.change_button_background_color(self.step_left[channel_index], color='black')
    #             self._set_voltage_display(channel_index)
    #         if self.gui.was_button_pressed(self.step_right[channel_index]) and not locked:
    #             self.gui.change_button_background_color(self.step_right[channel_index], color='red')
    #             self.pos.n_steps(channel_index, n=params[0])
    #             time.sleep(0.15)
    #             self.gui.change_button_background_color(self.step_right[channel_index], color='black')
    #             self._set_voltage_display(channel_index)

    #         # Handle walk event
    #         walker = self.walk_left[channel_index]
    #         if self.gui.was_button_pressed(walker) and not locked:
    #             self._walk(channel_index, walker, params, left=True)
    #         walker = self.walk_right[channel_index]
    #         if self.gui.was_button_pressed(walker) and not locked:
    #             self._walk(channel_index,walker, params, left=False)

    #         # Handle GUI Saving and Loading
    #         self._load_save_settings()

    #         # Update the previous values for future use
    #         (
    #             self.prev_amplitude[channel_index],
    #             self.prev_frequency[channel_index],
    #             self.prev_velocity[channel_index]
    #         ) = params[2], params[3], params[4]

    #         # If we want to override the previous DC voltage reading
    #         if not self.voltage_override and not voltage_failure:
    #             self.prev_voltage[channel_index] = params[5]
    #         else:
    #             self.voltage_override = False

    #         if self.gui.was_button_pressed('emergency_button'):
    #             self.stop_all()

    def get_GUI_parameters(self, channel):
        """ Gets the current GUI parameters for a given channel

        :param channel: (int) channel index (from 0)

        :return: (tuple) params in order n_steps, is_moving, amplitude, frequency, velocity, voltage
        """

        return (
            self.widgets['n_steps'][channel].value(),
            self.widgets['is_moving'][channel].isChecked(),
            self.widgets['amplitude'][channel].value(),
            self.widgets['frequency'][channel].value(),
            self.widgets['velocity'][channel].value(),
            self.widgets['voltage'][channel].value()
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
        self.widgets['voltage'][channel].setValue(voltage)
        self.voltage_override = True

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

    def save(self):
        """Saves or loads settings if relevant"""

        scalars = []
        for save_item in self.save_params:
            scalars += save_item
        self.gui.save_gui(
            self.gui.get_text('config_label'),
            logger=self.log,
            scalars=scalars
        )

    def _lock_stack(self, stack):
        """ Locks/unlocks a particular stack"""

        if self.lock_status[stack]:
            self.lock_status[stack] = False
            self.widgets['lock_button'][stack].setStyleSheet(
                'background-color:green'
            )
            self.widgets['lock_button'][stack].setText('Lock')
        else:
            self.lock_status[stack] = True
            self.widgets['lock_button'][stack].setStyleSheet(
                'background-color:red'
            )
            self.widgets['lock_button'][stack].setText('Unlock')

    def _is_axis_locked(self, channel):
        """ Checks if an axis is locked and returns boolean

        :param channel: (int) axis to check
        :return: (bool) whether or not the axis is currently locked
        """

        for index, ordering in enumerate(self.AXIS_ORDER):
            if channel in ordering:
                locked = self.lock_status[index]

        return locked
    
    def _step_left(self, channel):
        """ Steps a particular channel if unlocked

        :param channel: (int) channel to step
        """

        if not self._is_axis_locked(channel):

            self.pos.n_steps(
                channel=channel,
                n=-self.widgets['n_steps'][channel].value()
            )
            self.widgets['step_left'][channel].setStyleSheet(
                'background-color:red'
            )

            if self.pos.is_moving(channel):

                self.widgets['is_moving'][channel].setChecked(True)
                while self.pos.is_moving(channel):
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)

            self.widgets['step_left'][channel].setStyleSheet(
                'background-color:black'
            )
    
    def _step_right(self, channel):
        """ Steps a particular channel if unlocked

        :param channel: (int) channel to step
        """

        if not self._is_axis_locked(channel):

            self.pos.n_steps(
                channel=channel,
                n=self.widgets['n_steps'][channel].value()
            )
            self.widgets['step_right'][channel].setStyleSheet(
                'background-color:red'
            )

            if self.pos.is_moving(channel):

                self.widgets['is_moving'][channel].setChecked(True)
                while self.pos.is_moving(channel):
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)

            self.widgets['step_right'][channel].setStyleSheet(
                'background-color:black'
            )

    def _walk_left(self, channel):

        if not self._is_axis_locked(channel):

            if not self.pos.is_moving(channel):
                self.widgets['walk_left'].setStyleSheet(
                    'background-color:red'
                )
                self.pos.move(channel, backward=True)

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)

                if not self.widgets['walk_left'][channel].isDown():
                    self.widgets['walk_left'].setStyleSheet(
                        'background-color:black'
                    )

    def _walk_right(self, channel):

        if not self._is_axis_locked(channel):

            if not self.pos.is_moving(channel):
                self.widgets['walk_right'].setStyleSheet(
                    'background-color:red'
                )
                self.pos.move(channel, backward=True)

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)

                if not self.widgets['walk_right'][channel].isDown():
                    self.widgets['walk_right'].setStyleSheet(
                        'background-color:black'
                    )
    
    def _update_voltage(self, channel, voltage):
        """ Updates the channels DC voltage

        :param channel: (int) channel to update
        :param voltage: (float) value of voltage to update ot
        """

        # If locked, get the current voltage and reset the GUI value to it
        if self._is_axis_locked(channel):
            self.widgets['voltage'][channel].setValue(
                self.pos.get_voltage(channel)
            )

        # Otherwise set the DC voltage
        else:
            self.pos.set_voltage(channel, voltage)
    
    def _setup_gui(self):
        """ Configures what all buttons do """

        self.gui.load_button.clicked.connect(self.load_settings)
        self.gui.save_button.clicked.connect(self.save)
        
        # Stack based items (common to 3 axes)
        for stack in range(int(self.NUM_CHANNELS/3)):

            # Lock button
            self.widgets['lock_button'][stack].clicked.connect(
                lambda: self._lock_stack(stack)
            )
        
        for channel in range(self.NUM_CHANNELS):

            # Step buttons
            self.widgets['step_left'][channel].clicked.connect(
                lambda: self._step_left(channel)
            )
            self.widgets['step_right'][channel].clicked.connect(
                lambda: self._step_right(channel)
            )

            # Walk buttons
            self.widgets['walk_left'][channel].pressed.connect(
                lambda: self._walk_left(channel)
            )
            self.widgets['walk_left'][channel].released.connect(
                lambda: self.pos.stop(channel)
            )
            self.widgets['walk_right'][channel].pressed.connect(
                lambda: self._walk_right(channel)
            )
            self.widgets['walk_right'][channel].released.connect(
                lambda: self.pos.stop(channel)
            )

            # Parameters
            self.widgets['voltage'][channel].valueChanged.connect(
                lambda state, channel=channel: self._update_voltage(
                    channel=channel,
                    voltage=state
                ) 
            )
            self.widgets['amplitude'][channel].valueChanged.connect(
                lambda state, channel=channel: self.pos.set_parameters(
                    channel=channel,
                    amplitude=state
                )
            )
            self.widgets['frequency'][channel].valueChanged.connect(
                lambda state, channel=channel: self.pos.set_parameters(
                    channel=channel,
                    frequency=state
                )
            )
            self.widgets['velocity'][channel].valueChanged.connect(
                lambda state, channel=channel: self.pos.set_parameters(
                    channel=channel,
                    dc_vel=state
                )
            )


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    nanopos_client = clients['mcs2']
    gui_client = guis['positioner_control']

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger, config=kwargs['config'])

    # Initialize parameters
    for channel_index in range(control.NUM_CHANNELS):
        params = control.get_GUI_parameters(channel_index)
        control.initialize_parameters(channel_index, params)

    try:
        control.load_settings()
    except Exception as e:
        logger.warn(e)
        logger.warn('Failed to load settings from config file')

    control.gui.app.exec_()

    # Mitigate warnings about unused variables
    if loghost and logport and params:
        pass
