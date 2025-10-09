import numpy as np
import copy

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import get_ip, unpack_launcher, get_gui_widgets, load_script_config, generate_widgets, find_client
from pylabnet.network.client_server import smaract_mcs2, attocube_anc300

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


# If in this list, set DC voltage to 0 after taking a step.
BROKEN_CHANNELS = []
ATTOCUBE_CHANNELS = [7, 3, 4, 6, 1, 5, 8, 0, 2] # obj x, obj y, obj z,  front x, front y, front z,  rear x, rear y, rear z

ATTOCUBE_CHANNEL_ORDER = [1, 2, 3, 1, 2, 3, 4, 5, 6] # obj x, obj y, obj z,  front x, front y, front z,  rear x, rear y, rear z

MATCHING_DICT = {
    '7': ATTOCUBE_CHANNEL_ORDER[0],
    '3': ATTOCUBE_CHANNEL_ORDER[1],
    '4': ATTOCUBE_CHANNEL_ORDER[2],
    '6': ATTOCUBE_CHANNEL_ORDER[3],
    '1': ATTOCUBE_CHANNEL_ORDER[4],
    '5': ATTOCUBE_CHANNEL_ORDER[5],
    '8': ATTOCUBE_CHANNEL_ORDER[6],
    '0': ATTOCUBE_CHANNEL_ORDER[7],
    '2': ATTOCUBE_CHANNEL_ORDER[8]
}
# obj x, obj y, obj z,  front x, front y, front z,  rear x, rear y, rear z

CAP_ACTION_INDEX = {
    '7': 6,
    '3': 7,
    '4': 8,
    '6': 0,
    '1': 1,
    '5': 2,
    '8': 3,
    '0': 4,
    '2': 5
}
# obj x, obj y, obj z,  front x, front y, front z,  rear x, rear y, rear z


# 0: objective; 1: front-rear
CONNECTION_DICT = {
    '7': 0,
    '3': 0,
    '4': 0,
    '6': 1,
    '1': 1,
    '5': 1,
    '8': 1,
    '0': 1,
    '2': 1
}

GREY_BUTTON_STYLESHEET = 'background-color:#54687A'


# Value to set DC voltage to after every step
MIDVOLTAGE = 50


def to_attocube_channel(mcs_channel):

    if not mcs_channel in ATTOCUBE_CHANNELS:
        return
    else:
        return MATCHING_DICT[str(mcs_channel)]


def to_attocube_connection(mcs_channel):

    if not mcs_channel in ATTOCUBE_CHANNELS:
        return
    else:
        return CONNECTION_DICT[str(mcs_channel)]


def to_attocube_cap_action(mcs_channel):

    if not mcs_channel in ATTOCUBE_CHANNELS:
        return
    else:
        return CAP_ACTION_INDEX[str(mcs_channel)]


class Controller:
    """ A script class for controlling attocubes positioners + interfacing with GUI"""

    NUM_CHANNELS = 9
    WIDGET_DICT = dict(
        step_left=NUM_CHANNELS, step_right=NUM_CHANNELS, walk_left=NUM_CHANNELS,
        walk_right=NUM_CHANNELS, n_steps=NUM_CHANNELS, is_moving=NUM_CHANNELS,
        amplitude=NUM_CHANNELS, frequency=NUM_CHANNELS, voltage=NUM_CHANNELS,
        lock_button=int(NUM_CHANNELS / 3), keyboard_change_combo=1, ground=9, get_capacitance=9, c_box=9,
    )

    DC_TOLERANCE = 0.1
    AXIS_ORDER = [[7, 3, 4], [6, 1, 5], [8, 0, 2]]

    def __init__(self, attocube_client_obj: attocube_anc300.Client, attocube_client_fr: attocube_anc300.Client,
                 gui='positioner_control_3attos', log_client=None, config=None, port=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui: name of .ui file ot use
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        :param config: (str) name of config file, optional
        :param port: (int) port number for update/script server
        """

        self.attocube_list = [attocube_client_obj, attocube_client_fr]

        self.log = LogHandler(logger=log_client)
        self.gui = Window(
            gui_template=gui,
            host=get_ip(),
            port=port
        )
        self.gui.apply_stylesheet()

        self.widgets = get_gui_widgets(self.gui, **self.WIDGET_DICT)
        self.save_params = generate_widgets(dict(
            n_steps=self.NUM_CHANNELS, amplitude=self.NUM_CHANNELS, frequency=self.NUM_CHANNELS
        ))

        # Additional attributes
        self.prev_amplitude = [50] * self.NUM_CHANNELS
        self.prev_frequency = [30] * self.NUM_CHANNELS
        self.prev_voltage = [50] * self.NUM_CHANNELS
        self.voltage_override = False
        self.config = config
        self.lock_status = [False] * int(self.NUM_CHANNELS / 3)
        self.released = [False] * self.NUM_CHANNELS
        self.gui.config_label.setText(self.config)

        # Configure all button and parameter updates
        self._setup_gui()

        # Setup shortcut to use keyboard to step fiber
        self.press_right = QShortcut(QKeySequence('Right'), self.gui)
        self.press_left = QShortcut(QKeySequence('Left'), self.gui)
        self.press_up = QShortcut(QKeySequence('Up'), self.gui)
        self.press_down = QShortcut(QKeySequence('Down'), self.gui)
        self.press_up_z = QShortcut(QKeySequence('PgUp'), self.gui)
        self.press_down_z = QShortcut(QKeySequence('PgDown'), self.gui)

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

        obj_names = ['step_left', 'step_right', 'step_left', 'step_right', 'step_right', 'step_left']
        obj_index = [7, 7, 3, 3, 4, 4]

        front_names = ['step_left', 'step_right', 'step_left', 'step_right', 'step_right', 'step_left']
        front_index = [6, 6, 1, 1, 5, 5]

        rear_names = ['step_right', 'step_left', 'step_right', 'step_left', 'step_right', 'step_left']
        rear_index = [8, 8, 0, 0, 2, 2]

        if binding_index == 0:
            names = obj_names
            index = obj_index

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
        :param params: (tuple) params in order n_steps, is_moving, amplitude, frequency, voltage
        """
        if channel not in ATTOCUBE_CHANNELS:
            return

        self.attocube_list[to_attocube_connection(channel)].set_step_voltage(to_attocube_channel(channel), voltage=params[2])
        self.attocube_list[to_attocube_connection(channel)].set_step_frequency(to_attocube_channel(channel), freq=params[3])

    def get_GUI_parameters(self, channel):
        """ Gets the current GUI parameters for a given channel

        :param channel: (int) channel index (from 0)

        :return: (tuple) params in order n_steps, is_moving, amplitude, frequency,  voltage
        """

        return (
            self.widgets['n_steps'][channel].value(),
            self.widgets['is_moving'][channel].isChecked(),
            self.widgets['amplitude'][channel].value(),
            self.widgets['frequency'][channel].value(),
            self.widgets['voltage'][channel].value()
        )

    def stop_all(self):
        """ Stops all channels """

        # Stop Attocubes
        for attocube in self.attocube_list:
            attocube.stop_all()

    def load_settings(self):
        """ Loads settings from configuration """
        self.gui.load_gui("mcs2_anc300_control",
                          self.gui.config_label.text(),
                          logger=self.log
                          )

    # Technical methods

    def _set_voltage_display(self, channel):
        """ Sets the voltage on the GUI to the current value measured by the controller

        :param channel: (int) channel index (from 0)
        """
        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        voltage = self.attocube_list[to_attocube_connection(channel)].get_offset_voltage(attocube_channel)
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
        self.log.info(f"Channel {channel}")

        if channel not in ATTOCUBE_CHANNELS:
            return

        attocube_channel = to_attocube_channel(channel)

        if not self._is_axis_locked(channel):

            self.attocube_list[to_attocube_connection(channel)].n_steps(
                channel=attocube_channel,
                n=-self.widgets['n_steps'][channel].value()
            )

            self.widgets['step_right'][channel].setStyleSheet(
                'background-color:red'
            )

            # if self.attocube.is_moving(attocube_channel):

            #     while self.attocube.is_moving(attocube_channel):
            #         self.widgets['is_moving'][channel].setCheckable(True)
            #         self.widgets['is_moving'][channel].setChecked(True)
            #         self.gui.force_update()
            #     self.widgets['is_moving'][channel].setChecked(False)
            #     self.widgets['is_moving'][channel].setCheckable(False)

            self.widgets['step_right'][channel].setStyleSheet(
                GREY_BUTTON_STYLESHEET
            )
            self._set_voltage_display(channel)

        else:
            self.log.info("LOCKED")

    def _step_right(self, channel: int):
        """ Steps a particular channel if unlocked

        :param channel: (int) channel to step
        """

        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        if not self._is_axis_locked(channel):

            self.attocube_list[to_attocube_connection(channel)].n_steps(
                channel=attocube_channel,
                n=self.widgets['n_steps'][channel].value()
            )

            self.widgets['step_right'][channel].setStyleSheet(
                'background-color:red'
            )

            # if self.attocube.is_moving(attocube_channel):

            #     while self.attocube.is_moving(attocube_channel):
            #         self.widgets['is_moving'][channel].setCheckable(True)
            #         self.widgets['is_moving'][channel].setChecked(True)
            #         self.gui.force_update()
            #     self.widgets['is_moving'][channel].setChecked(False)
            #     self.widgets['is_moving'][channel].setCheckable(False)

            self.widgets['step_right'][channel].setStyleSheet(
                GREY_BUTTON_STYLESHEET
            )
            self._set_voltage_display(channel)

    def _walk_left(self, channel: int):
        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        if not self._is_axis_locked(channel):

            if not self.attocube_list[to_attocube_connection(channel)].is_moving(attocube_channel):
                self.widgets['walk_left'][channel].setStyleSheet(
                    'background-color:red'
                )
                self.attocube_list[to_attocube_connection(channel)].move(attocube_channel, backward=True)

                while self.attocube_list[to_attocube_connection(channel)].is_moving(attocube_channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

                if not self.widgets['walk_left'][channel].isDown():
                    self.widgets['walk_left'][channel].setStyleSheet(
                        GREY_BUTTON_STYLESHEET
                    )

                self._set_voltage_display(channel)

    def _walk_right(self, channel: int):
        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        if not self._is_axis_locked(channel):

            if not self.attocube_list[to_attocube_connection(channel)].is_moving(attocube_channel):
                self.widgets['walk_right'][channel].setStyleSheet(
                    'background-color:red'
                )
                self.attocube_list[to_attocube_connection(channel)].move(attocube_channel, backward=False)

                while self.attocube_list[to_attocube_connection(channel)].is_moving(attocube_channel):
                    self.widgets['is_moving'][channel].setCheckable(True)
                    self.widgets['is_moving'][channel].setChecked(True)
                    self.gui.force_update()
                self.widgets['is_moving'][channel].setChecked(False)
                self.widgets['is_moving'][channel].setCheckable(False)

                if not self.widgets['walk_right'][channel].isDown():
                    self.widgets['walk_right'][channel].setStyleSheet(
                        GREY_BUTTON_STYLESHEET
                    )

                self._set_voltage_display(channel)

    def _stop(self, channel):
        if channel in ATTOCUBE_CHANNELS:
            attocube_channel = to_attocube_channel(channel)
            self.attocube_list[to_attocube_connection(channel)].stop(attocube_channel)

    def _update_voltage(self, channel: int, voltage: float):
        """ Updates the channels DC voltage

        :param channel: (int) channel to update
        :param voltage: (float) value of voltage to update ot
        """

        if channel in ATTOCUBE_CHANNELS:
            attocube = True
            attocube_channel = to_attocube_channel(channel)
        else:
            attocube = False

        self.log.info(f"Channel {channel} moved.")

        if attocube:
            self.attocube_list[to_attocube_connection(channel)].set_offset_voltage(
                channel=attocube_channel,
                voltage=voltage
            )

    def _update_amplitude(self, channel, amplitude):
        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        self.attocube_list[to_attocube_connection(channel)].set_step_voltage(
            channel=attocube_channel,
            voltage=amplitude
        )

    def _update_frequency(self, channel, frequency):
        if channel not in ATTOCUBE_CHANNELS:
            return
        attocube_channel = to_attocube_channel(channel)

        self.attocube_list[to_attocube_connection(channel)].set_step_frequency(
            channel=attocube_channel,
            freq=frequency
        )

    def _update_velocity(self, channel, dc_vel):
        return

    def _measure_set_C(self, channel):
        self.log.info('measure channel:' + str(channel))
        cap = self.attocube_list[to_attocube_connection(channel)].get_capacitance(to_attocube_channel(channel))
        self.widgets['c_box'][to_attocube_cap_action(channel)].setValue(int(cap))

    def _setup_gui(self):
        """ Configures what all buttons do """

        self.gui.load_button.clicked.connect(self.load_settings)
        self.gui.save_button.clicked.connect(self.save)
        self.gui.emergency_button.clicked.connect(self.stop_all)

        # Stack based items (common to 3 axes)
        for stack in range(int(self.NUM_CHANNELS / 3)):

            stack_no = copy.deepcopy(stack)

            # Lock button
            self.widgets['lock_button'][stack].pressed.connect(
                lambda stack=stack_no: self._lock_stack(stack)
            )

        for channel in range(self.NUM_CHANNELS):

            # Step buttons
            self.widgets['step_left'][channel].pressed.connect(
                lambda channel=channel: self._step_left(channel)
            )
            self.widgets['step_right'][channel].pressed.connect(
                lambda channel=channel: self._step_right(channel)
            )

            # Walk buttons
            self.widgets['walk_left'][channel].pressed.connect(
                lambda channel=channel: self._walk_left(channel)
            )
            self.widgets['walk_left'][channel].released.connect(
                lambda channel=channel: self._stop(channel)
            )
            self.widgets['walk_right'][channel].pressed.connect(
                lambda channel=channel: self._walk_right(channel)
            )
            self.widgets['walk_right'][channel].released.connect(
                lambda channel=channel: self._stop(channel)
            )

            # Parameters
            self.widgets['voltage'][channel].valueChanged.connect(
                lambda state, channel=channel: self._update_voltage(
                    channel=channel,
                    voltage=state
                )
            )
            self.widgets['amplitude'][channel].valueChanged.connect(
                lambda state, channel=channel: self._update_amplitude(
                    channel=channel,
                    amplitude=state
                )
            )
            self.widgets['frequency'][channel].valueChanged.connect(
                lambda state, channel=channel: self._update_frequency(
                    channel=channel,
                    frequency=state
                )
            )

        self.widgets['ground'][to_attocube_cap_action(0)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(0)].ground(to_attocube_channel(0))
        )

        self.widgets['ground'][to_attocube_cap_action(1)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(1)].ground(to_attocube_channel(1))
        )

        self.widgets['ground'][to_attocube_cap_action(2)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(2)].ground(to_attocube_channel(2))
        )

        self.widgets['ground'][to_attocube_cap_action(3)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(3)].ground(to_attocube_channel(3))
        )
        self.widgets['ground'][to_attocube_cap_action(4)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(4)].ground(to_attocube_channel(4))
        )
        self.widgets['ground'][to_attocube_cap_action(5)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(5)].ground(to_attocube_channel(5))
        )

        self.widgets['ground'][to_attocube_cap_action(6)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(6)].ground(to_attocube_channel(6))
        )
        self.widgets['ground'][to_attocube_cap_action(7)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(7)].ground(to_attocube_channel(7))
        )
        self.widgets['ground'][to_attocube_cap_action(8)].pressed.connect(
            lambda: self.attocube_list[to_attocube_connection(8)].ground(to_attocube_channel(8))
        )

        self.widgets['get_capacitance'][to_attocube_cap_action(0)].pressed.connect(
            lambda: self._measure_set_C(0)
        )
        self.widgets['c_box'][to_attocube_cap_action(0)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(1)].pressed.connect(
            lambda: self._measure_set_C(1)
        )
        self.widgets['c_box'][to_attocube_cap_action(1)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(2)].pressed.connect(
            lambda: self._measure_set_C(2)
        )
        self.widgets['c_box'][to_attocube_cap_action(2)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(3)].pressed.connect(
            lambda: self._measure_set_C(3)
        )
        self.widgets['c_box'][to_attocube_cap_action(3)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(4)].pressed.connect(
            lambda: self._measure_set_C(4)
        )
        self.widgets['c_box'][to_attocube_cap_action(4)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(5)].pressed.connect(
            lambda: self._measure_set_C(5)
        )
        self.widgets['c_box'][to_attocube_cap_action(5)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(6)].pressed.connect(
            lambda: self._measure_set_C(6)
        )
        self.widgets['c_box'][to_attocube_cap_action(6)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(7)].pressed.connect(
            lambda: self._measure_set_C(7)
        )
        self.widgets['c_box'][to_attocube_cap_action(7)].setSuffix(' nF')

        self.widgets['get_capacitance'][to_attocube_cap_action(8)].pressed.connect(
            lambda: self._measure_set_C(8)
        )
        self.widgets['c_box'][to_attocube_cap_action(8)].setSuffix(' nF')


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(script='mcs2_anc300_control',
                                config=kwargs['config'],
                                logger=logger)
    attocube_client_obj = find_client(clients=clients, settings=config, client_type='anc300', client_config='l500_attocubes_obj')
    attocube_client_fr = find_client(clients=clients, settings=config, client_type='anc300', client_config='l500_attocubes_front_rear')

    gui_client = 'positioner_control_3attos'

    # Instantiate controller
    control = Controller(attocube_client_obj, attocube_client_fr, gui_client, logger, config=kwargs['config'], port=kwargs['server_port'])

    # Initialize parameters
    for channel_index in range(control.NUM_CHANNELS):
        params = control.get_GUI_parameters(channel_index)
        control.initialize_parameters(channel_index, params)

    # try:
    #     control.load_settings()
    # except Exception as e:
    #     logger.warn(e)
    #     logger.warn('Failed to load settings from config file')

    control.gui.app.exec_()

    # Mitigate warnings about unused variables
    if loghost and logport and params:
        pass
