import numpy as np
import time
import socket
import copy

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import get_ip, unpack_launcher, get_gui_widgets, load_script_config, generate_widgets, find_client
from pylabnet.network.client_server import smaract_mcs2

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import  QShortcut


class Controller:
    """ A script class for controlling MCS2 positioners + interfacing with GUI"""

    NUM_CHANNELS = 9
    WIDGET_DICT = dict(
        step_left=NUM_CHANNELS, step_right=NUM_CHANNELS, walk_left=NUM_CHANNELS,
        walk_right=NUM_CHANNELS, n_steps=NUM_CHANNELS, is_moving=NUM_CHANNELS,
        amplitude=NUM_CHANNELS, frequency=NUM_CHANNELS, velocity=NUM_CHANNELS, voltage=NUM_CHANNELS,
        lock_button=int(NUM_CHANNELS/3), keyboard_change_combo=1
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
            host=get_ip(),
            port=port
        )
        self.gui.apply_stylesheet()

        self.widgets = get_gui_widgets(self.gui, **self.WIDGET_DICT)
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
        self.gui.config_label.setText(self.config)

        # Configure all button and parameter updates
        self._setup_gui()


        # Setup shortcut to use keyboard to step fiber
        self.press_right = QShortcut(QKeySequence('Right'), self.gui)
        self.press_left = QShortcut(QKeySequence('Left'), self.gui)
        self.press_up = QShortcut(QKeySequence('Up'), self.gui)
        self.press_down = QShortcut(QKeySequence('Down'), self.gui)
        self.press_up_z = QShortcut(QKeySequence('PgUp'), self.gui)
        self.press_down_z= QShortcut(QKeySequence('PgDown'), self.gui)

        self.widgets['keyboard_change_combo'].currentIndexChanged.connect(self._bind_arrow_keys)


    def _disconnect_arrow_keys(self):
        """ Unbinds the arrow, up/down keys from any actions."""
        self.press_right.activated.disconnect()
        self.press_left.activated.disconnect()
        self.press_up.activated.disconnect()
        self.press_down.activated.disconnect()
        self.press_up_z.activated.disconnect()
        self.press_down_z.activated.disconnect()


    def _bind_arrow_keys(self):
        """ Binds arroy keys on keyboard to step around front fiber."""

        try:
            self._disconnect_arrow_keys()
        except TypeError:
            self.log.info('Initial call of arrowkey binding.')

        binding_index = self.widgets['keyboard_change_combo'].currentIndex()

        front_names = ['step_left', 'step_right', 'step_left', 'step_right', 'step_right', 'step_left']
        front_index = [6, 6, 1, 1, 5, 5]

        rear_names = ['step_right', 'step_left',  'step_right',  'step_left', 'step_right', 'step_left']
        rear_index = [8, 8, 0, 0, 2, 2]

        if binding_index == 0:
            return
        if binding_index == 1:
            names = front_names
            index = front_index
        elif binding_index == 2:
            names = rear_names
            index = rear_index

        self.press_right.activated.connect(lambda: self.widgets[names[0]][index[0]].animateClick())
        self.press_left.activated.connect(lambda: self.widgets[names[1]][index[1]].animateClick())
        self.press_up.activated.connect(lambda: self.widgets[names[2]][index[2]].animateClick())
        self.press_down.activated.connect(lambda: self.widgets[names[3]][index[3]].animateClick())
        self.press_up_z.activated.connect(lambda: self.widgets[names[4]][index[4]].animateClick())
        self.press_down_z.activated.connect(lambda: self.widgets[names[5]][index[5]].animateClick())


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
        self.gui.load_gui("mcs2_control",
            self.gui.config_label.text(),
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

    def _lock_stack(self, stack: int):
        """ Locks/unlocks a particular stack"""

        if self.lock_status[stack]:
            self.lock_status[stack] = False
            self.widgets['lock_button'][stack].setStyleSheet(
                'background-color:rgb(100,0,0)'
            )
            self.widgets['lock_button'][stack].setText('Lock')
        else:
            self.lock_status[stack] = True
            self.widgets['lock_button'][stack].setStyleSheet(
                'background-color:rgb(0,100,0)'
            )
            self.widgets['lock_button'][stack].setText('Unlock')

    def _is_axis_locked(self, channel: int):
        """ Checks if an axis is locked and returns boolean

        :param channel: (int) axis to check
        :return: (bool) whether or not the axis is currently locked
        """

        for index, ordering in enumerate(self.AXIS_ORDER):
            if channel in ordering:
                locked = self.lock_status[index]

        return locked

    def _step_left(self, channel: int):
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

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

            self.widgets['step_left'][channel].setStyleSheet(
                'background-color:black'
            )

            self._set_voltage_display(channel)

    def _step_right(self, channel: int):
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

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

            self.widgets['step_right'][channel].setStyleSheet(
                'background-color:black'
            )

            self._set_voltage_display(channel)

    def _walk_left(self, channel: int):

        if not self._is_axis_locked(channel):

            if not self.pos.is_moving(channel):
                self.widgets['walk_left'][channel].setStyleSheet(
                    'background-color:red'
                )
                self.pos.move(channel, backward=True)

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

                if not self.widgets['walk_left'][channel].isDown():
                    self.widgets['walk_left'][channel].setStyleSheet(
                        'background-color:black'
                    )

                    self._set_voltage_display(channel)

    def _walk_right(self, channel: int):

        if not self._is_axis_locked(channel):

            if not self.pos.is_moving(channel):
                self.widgets['walk_right'][channel].setStyleSheet(
                    'background-color:red'
                )
                self.pos.move(channel, backward=False)

                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

                if not self.widgets['walk_right'][channel].isDown():
                    self.widgets['walk_right'][channel].setStyleSheet(
                        'background-color:black'
                    )

                    self._set_voltage_display(channel)

    def _update_voltage(self, channel: int, voltage: float):
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

            if self.pos.is_moving(channel):
                while self.pos.is_moving(channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

    def _setup_gui(self):
        """ Configures what all buttons do """

        self.gui.load_button.clicked.connect(self.load_settings)
        self.gui.save_button.clicked.connect(self.save)
        self.gui.emergency_button.clicked.connect(self.stop_all)

        # Stack based items (common to 3 axes)
        for stack in range(int(self.NUM_CHANNELS/3)):

            stack_no = copy.deepcopy(stack)

            # Lock button
            self.widgets['lock_button'][stack].pressed.connect(
                lambda stack=stack_no: self._lock_stack(stack)
            )

        for channel in range(self.NUM_CHANNELS):

            channel_no = copy.deepcopy(channel)

            # Step buttons
            self.widgets['step_left'][channel_no].pressed.connect(
                lambda channel=channel_no: self._step_left(channel)
            )
            self.widgets['step_right'][channel_no].pressed.connect(
                lambda channel=channel_no: self._step_right(channel)
            )

            # Walk buttons
            self.widgets['walk_left'][channel_no].pressed.connect(
                lambda channel=channel_no: self._walk_left(channel)
            )
            self.widgets['walk_left'][channel_no].released.connect(
                lambda channel=channel_no: self.pos.stop(channel)
            )
            self.widgets['walk_right'][channel_no].pressed.connect(
                lambda channel=channel_no: self._walk_right(channel)
            )
            self.widgets['walk_right'][channel_no].released.connect(
                lambda channel=channel_no: self.pos.stop(channel)
            )

            # Parameters
            self.widgets['voltage'][channel_no].valueChanged.connect(
                lambda state, channel=channel_no: self._update_voltage(
                    channel=channel,
                    voltage=state
                )
            )
            self.widgets['amplitude'][channel_no].valueChanged.connect(
                lambda state, channel=channel_no: self.pos.set_parameters(
                    channel=channel,
                    amplitude=state
                )
            )
            self.widgets['frequency'][channel_no].valueChanged.connect(
                lambda state, channel=channel_no: self.pos.set_parameters(
                    channel=channel,
                    frequency=state
                )
            )
            self.widgets['velocity'][channel_no].valueChanged.connect(
                lambda state, channel=channel_no: self.pos.set_parameters(
                    channel=channel,
                    dc_vel=state
                )
            )


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(script='mcs2_control',
                        config=kwargs['config'],
                        logger=logger)
    nanopos_client = find_client(clients=clients, settings=config, client_type='mcs2')
    gui_client = 'positioner_control'

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger, config=kwargs['config'], port=kwargs['server_port'])

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
