from pylabnet.scripts.pid import PID
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase

from pylabnet.gui.pyqt.gui_handlers.wavemeter.wavemeter_gui_handler import WavemeterGUIHandler


import numpy as np
import time
import copy
import pickle


# Static methods


# Core objects

class WlmMonitor:
    """ A script class for monitoring and locking lasers based on the wavemeter """


    def __init__(self,  wlm_client, gui_client, ao_clients=None, display_pts=5000, threshold=0.0002):
        """ TBD
        """

        # Instanciate Gui handler
        self.gui_handler = WavemeterGUIHandler(wlm_client, gui_client, ao_clients=None, display_pts=5000, threshold=0.0002)


class Channel:
    """Object containing all information regarding a single wavemeter channel"""

    # Set acceptable voltage range for laser modulation
    _min_voltage = -10
    _max_voltage = 10

    # Gain multiplier for PID
    _gain = 1000

    def __init__(self, channel_params, ao_clients=None):
        """
        Initializes all parameters given, sets others to default. Also sets up some defaults + placeholders for data

        :param channel_params: (dict) Dictionary of channel parameters (see WlmMonitor.set_parameters() for details)
        :param ao_clients: (dict, optional) Dictionary containing AO clients tying a keyname string to the actual client
        """

        # Set channel parameters to default values
        self.ao_clients = ao_clients
        self.ao = None  # Dict with client name and channel for AO to use
        self.voltage = None  # Array of voltage values for AO, used for plotting/monitoring voltage
        self.current_voltage = 0
        self.setpoint = None
        self.lock = False
        self.error = None  # Array of error values, used for plotting/monitoring lock error
        self.labels_updated = False  # Flag to check if we have updated all labels
        self.setpoint_override = True  # Flag to check if setpoint has been updated + GUI should be overridden
        self.lock_override = True  # Flag to check if lock has been updated + GUI should be overridden
        self.gui_setpoint = 0  # Current GUI setpoint
        self.gui_lock = False  # Current GUI lock boolean
        self.prev_gui_lock = None  # Previous GUI lock boolean
        self.prev_gui_setpoint = None  # Previous GUI setpoint

        # Set all relevant parameters to default values
        self._overwrite_parameters(channel_params)

        # Initialize relevant placeholders
        self.data = np.array([])
        self.sp_data = np.array([])

    def initialize(self, wavelength, display_pts=5000):
        """
        Initializes the channel based on the current wavelength

        :param wavelength: current wavelength
        :param display_pts: number of points to display on the plot
        """

        self.data = np.ones(display_pts) * wavelength

        if self.setpoint is not None:
            self.sp_data = np.ones(display_pts) * self.setpoint
            self.setpoint_override = True

        self.lock_override = True

        # Initialize voltage and error
        if self.voltage is not None:
            self.voltage = np.ones(display_pts) * self.current_voltage

            # Check that setpoint is reasonable, otherwise set error to 0
            if self.setpoint is None:
                self.error = np.zeros(display_pts)
            else:
                self.error = np.ones(display_pts) * (wavelength - self.setpoint)

    def initialize_sp_data(self, display_pts=5000):
        if self.setpoint is not None:
            self.sp_data = np.ones(display_pts) * self.setpoint

    def update(self, wavelength):
        """
        Updates the data, setpoints, and all locks

        :param wavelength: (float) current wavelength
        """

        self.data = np.append(self.data[1:], wavelength)

        if self.setpoint is not None:

            # Pick which setpoint to use
            # If the setpoint override is on, this means we need to try and set the GUI value to self.setpoint
            if self.setpoint_override:

                # Check if the GUI has actually caught up
                if self.setpoint == self.gui_setpoint:
                    self.setpoint_override = False

                # Otherwise, the GUI still hasn't implemented the setpoint prescribed by update_parameters()

            # If setpoint override is off, this means the GUI caught up to our last update_parameters() call, and we
            # should refrain from updating the value until we get a new value from the GUI
            else:

                # Check if the GUI has changed, and if so, update the setpoint in the script to match
                if self.gui_setpoint != self.prev_gui_setpoint:
                    self.setpoint = copy.deepcopy(self.gui_setpoint)

                # Otherwise the GUI is static AND parameters haven't been updated so we don't change the setpoint at all

            # Store the latest GUI setpoint
            self.prev_gui_setpoint = copy.deepcopy(self.gui_setpoint)
            self.sp_data = np.append(self.sp_data[1:], self.setpoint)

        # Now deal with PID stuff
        self.pid.set_parameters(setpoint=0 if self.setpoint is None else self.setpoint)

        # Implement lock
        # Set process variable
        self.pid.set_pv(pv=self.data[len(self.data) - self.memory:])
        # Set control variable
        self.pid.set_cv()

        # See logic for setpoint above
        if self.lock_override:
            if self.lock == self.gui_lock:
                self.lock_override = False
        else:
            if self.gui_lock != self.prev_gui_lock:
                self.lock = copy.deepcopy(self.gui_lock)

        self.prev_gui_lock = copy.deepcopy(self.gui_lock)

        if self.lock:
            try:
                if self.ao is not None:
                    if self._min_voltage <= self.current_voltage + self.pid.cv * self._gain <= self._max_voltage:
                        self.current_voltage += self.pid.cv * self._gain
                    elif self.current_voltage + self.pid.cv * self._gain < self._min_voltage:
                        self.current_voltage = self._min_voltage
                    else:
                        self.current_voltage = self._max_voltage
                    self.ao['client'].set_ao_voltage(
                        ao_channel=self.ao['channel'],
                        voltages=[self.current_voltage]
                    )
            except EOFError:
                self.ao = None

        # Update voltage and error data
        if self.voltage is not None:
            self.voltage = np.append(self.voltage[1:], self.current_voltage)
            self.error = np.append(self.error[1:], self.pid.error * self._gain)
        else:
            print('Voltage is None')

    def zero_voltage(self):
        """Zeros the voltage (if applicable)"""

        try:
            if self.ao is not None:
                self.ao['client'].set_ao_voltage(
                    ao_channel=self.ao['channel'],
                    voltages=[0]
                )
                self.current_voltage = 0
        except EOFError:
            self.ao = None

    def _overwrite_parameters(self, channel_params):
        """ Sets all internal channel parameters to input

        If parameters are not given, they are overwritten to defaults - see implementation below, as well as the
        WlmMonitor.set_parameters() docstring for default details

        :param channel_params: (dict) dictionary containing all parameters. See WlmMonitor.set_parameters() for details
        """

        # Initialize all given attributes, otherwise initialize defaults
        if 'channel' in channel_params:
            self.number = channel_params['channel']
        else:

            # By default use channel 1
            self.number = 1

        if 'name' in channel_params:
            self.name = channel_params['name']
        else:

            # Initialize some random channel name if not given
            self.name = 'Channel ' + str(np.random.randint(1000000))
        self.curve_name = self.name + ' Frequency'  # Name used for identifying the frequency Curve object
        self.lock_name = self.name + ' Lock'  # Name used for identifying lock Scalar object
        self.error_name = self.name + ' Error'  # Name used for identifying error Scalar object

        if 'setpoint' in channel_params:
            self.setpoint = channel_params['setpoint']
        else:
            self.setpoint = None
        self.setpoint_name = self.name + ' Setpoint'  # Name used for identifying setpoint Curve object

        if 'lock' in channel_params:
            self.lock = channel_params['lock']
        else:
            self.lock = False

        if 'memory' in channel_params:
            self.memory = channel_params['memory']
        else:
            self.memory = 20

        if 'PID' in channel_params:
            self.pid = PID(
                p=channel_params['PID']['p'],
                i=channel_params['PID']['i'],
                d=channel_params['PID']['d'],
                memory=self.memory,
                setpoint=0 if self.setpoint is None else self.setpoint
            )
        else:

            # Just initialize a default PID module
            self.pid = PID()

        if 'AO' in channel_params and self.ao_clients is not None:

            # Convert AO from string to object using lookup
            try:
                self.ao = {
                    'client': self.ao_clients[channel_params['AO']['client']],
                    'channel': channel_params['AO']['channel']
                }
            except KeyError:
                # Alert the user that AO initialization failed
                self.ao = None
                print('Failed to initialize AO for Channel {}'.format(self.number))

        # If AO is not given just leave it as None
        else:
            self.ao = None

        # Configure voltage monitor arrays if desired
        if 'voltage_monitor' in channel_params:
            if channel_params['voltage_monitor']:
                self.voltage = np.array([])
                self.error = np.array([])
                self.aux_name = '{} Auxiliary Monitor'.format(self.name)
                self.voltage_curve = '{} Voltage'.format(self.name)
                self.error_curve = '{} Lock Error'.format(self.name)
            else:
                self.voltage = None

        # Set voltage to None - this will be used later on to check if we should be monitoring
        else:
            self.voltage = None

        # If we specify a specific widget to use, configure an offset for plot widget loading
        if 'plot_widget' in channel_params:
            self.plot_widget_offset = channel_params['plot_widget']

        # Otherwise just use the default widget (populates in order)
        else:
            self.plot_widget_offset = 0