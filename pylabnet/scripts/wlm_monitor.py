from pylabnet.scripts.pid import PID
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase

import numpy as np
import time
import copy
import pickle


# Static methods

def generate_widgets():
    """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""

    graphs, legends, numbers, booleans, labels, events = [], [], [], [], [], []
    for i in range(4):
        graphs.append('graph_widget_' + str(i + 1))
        legends.append('legend_widget_' + str(i + 1))
        numbers.append('number_widget_' + str(i + 1))
        booleans.append('boolean_widget_' + str(i + 1))
        labels.append('label_' + str(i + 1))
        events.append('event_button_' + str(i + 1))
    for i in range(4, 8):
        numbers.append('number_widget_' + str(i + 1))
        booleans.append('boolean_widget_' + str(i + 1))
        labels.append('label_' + str(i + 1))
    return graphs, legends, numbers, booleans, labels, events


# Core objects

class WlmMonitor:
    """ A script class for monitoring and locking lasers based on the wavemeter """

    # Assign widget names based on .gui file.
    (_graph_widgets,
     _legend_widgets,
     _number_widgets,
     _boolean_widgets,
     _label_widgets,
     _event_widgets) = generate_widgets()

    def __init__(self, wlm_client, gui_client, ao_clients=None, display_pts=5000, threshold=0.0002):
        """ Instantiates WlmMonitor script object for monitoring wavemeter

        :param wlm_client: (obj) instance of wavemeter client
        :param gui_client: (obj) instance of GUI client.
        :param ao_clients: (dict, optional) dictionary of AO client objects with keys to identify. Exmaple:
            {'ni_usb_1': nidaqmx_usb_client_1, 'ni_usb_2': nidaqmx_usb_client_2, 'ni_pxi_multi': nidaqmx_pxi_client}
        :param display_pts: (int, optional) number of points to display on plot
        :param threshold: (float, optional) threshold in THz for lock error signal
        """

        self.channels = []  # Stores a list of channels that have been instantiated (ideally independent WLM channels)
        self.is_running = False  # Flag which lets us know if WlmMonitor is running
        self.is_paused = False  # Flag which tells us we have simply paused WlmMonitor operation
        self._gui_connected = False  # Flag which alerts if a GUI client has been connected successfully
        self._gui_reconnect = False  # Flag which tells us to try reconnecting to the GUI client

        self.wlm_client = wlm_client
        self.gui = gui_client
        self.ao_clients = ao_clients
        self.display_pts = display_pts
        self.threshold = threshold

    def set_parameters(self, channel_params):
        """ Instantiates new channel objects with given parameters and assigns them to the WlmMonitor

        Note: parameters for a channel that has already been assigned can be set or updated later using the
        update_parameters() method via an update client in a separate python process.

        :param channel_params: (list) of dictionaries containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'PID': {'p': 1, 'i': 0.1, 'd': 0}, 'AO': {'client':'nidaqmx_client', 'channel': 'ao1'},
             'voltage_monitor': True}

            In more detail:
            - 'channel': should be from 1-8 for the High-Finesse Wavemeter (with switch) and should ALWAYS be provided,
                as a reference so that we know which channel to assign all the other parameters to
            - 'name': a string that can just be provided once and is used as a user-friendly name for the channel.
                Initializes to 'Channel X' where X is a random integer if not provided
            - 'setpoint': setpoint for this channel. If not provided, or if None, the setpoint is not plotted/tracked
            - 'lock': boolean that tells us whether or not to turn on the lock. Ignored if setpoint is None. Default is
                False.
            - 'memory': Number of points for integral memory of PID (history of the integral). Default is 20.
            - 'PID': dict containing PID parameters. Uses the pylabnet.scripts.PID module. By default instantiates the
                default PID() object.
            - 'AO': dict containing two elements: 'client' which is a string that is the name of the AO client to use
                for locking. This should match up with a key in self.ao_clients. 'channel'is an identifier for which
                analog output to use for this channel. By default it is set to None and no active locking is performed
            - 'voltage monitor': boolean which tells us whether to also plot/track the AO voltage + setpoint error on
                the plot below the laser graph. Default is False
        """

        # Check if it is only a single channel
        if type(channel_params) is dict:
            channel_params = [channel_params]

        # Initialize each channel individually
        for channel_param_set in channel_params:
            self.channels.append(Channel(channel_param_set, self.ao_clients))

    def update_parameters(self, parameters):
        """ Updates only the parameters given. Can be used in the middle of the script operation via an update client.

        :param parameters: (list) list of dictionaries, see set_parameters() for details
        """

        for parameter in parameters:

            # Make sure a channel is given
            if 'channel' in parameter:

                # Check if it is a channel that is already logged
                channel_list = self._get_channels()
                if parameter['channel'] in channel_list:

                    # Find index of the desired channel
                    channel = self.channels[channel_list.index(parameter['channel'])]

                    # Set all other parameters for this channel
                    if 'name' in parameter:
                        channel.name = parameter['name']

                    if 'setpoint' in parameter:

                        # If the setpoint didn't exist and now exists, we need to update and add a curve
                        if channel.setpoint is None and parameter['setpoint'] is not None:
                            self.gui.assign_curve(
                                plot_label=channel.name,
                                curve_label=channel.setpoint_name
                            )
                            channel.setpoint = parameter['setpoint']
                            channel.pid.set_parameters(setpoint=channel.setpoint)
                            channel.initialize_sp_data()

                        # If the setpoint existed and is now removed, delete the curve item
                        elif channel.setpoint is not None and parameter['setpoint'] is None:
                            self.gui.remove_curve(
                                plot_label=channel.name,
                                curve_label=channel.setpoint_name
                            )
                            channel.setpoint = None
                            channel.pid.set_parameters(setpoint=0)

                        # Otherwise just update the setpoint normally
                        else:
                            channel.setpoint = parameter['setpoint']

                            # Mark that we should override GUI setpoint, since it has been updated by the script
                            channel.setpoint_override = True

                    if 'lock' in parameter:
                        channel.lock = parameter['lock']

                        # Mark that we should override the GUI lock since it has been updated by the script
                        channel.lock_override = True

                    if 'memory' in parameter:
                        channel.memory = parameter['memory']
                    if 'PID' in parameter:
                        channel.pid.set_parameters(
                            p=parameter['PID']['p'],
                            i=parameter['PID']['i'],
                            d=parameter['PID']['d'],
                        )

                    # Ignore AO requests if clients have not been assigned
                    if 'AO' in parameter and self.ao_clients is not None:

                        # Convert AO from string to object using lookup
                        try:
                            channel.ao = {
                                'client': self.ao_clients[parameter['AO']['client']],
                                'channel': parameter['AO']['channel']
                            }

                        # Handle case where the AO client does not exist
                        except KeyError:
                            channel.ao = None

                # Otherwise, it is a new channel so we should add it
                else:
                    self.channels.append(Channel(parameter))
                    self._initialize_channel(
                        index=len(self.channels) - 1,
                        channel=self.channels[-1]
                    )

    def initialize_channels(self):
        """Initializes all channels and outputs to the GUI"""

        for index, channel in enumerate(self.channels):
            self._initialize_channel(index, channel)

    def clear_channel(self, channel):
        """ Clears the plot output for this channel

        :param channel: channel number to clear
        """

        # Get the relevant channel
        channel_list = self._get_channels()

        try:
            channel = self.channels[channel_list.index(channel)]
            channel.initialize(channel.data[-1])

        # If the channel isn't monitored
        except KeyError:
            pass

    def run(self):
        """Runs the WlmMonitor continuously

        Can be stopped using the pause() method
        """

        # Mark running flag
        self.is_running = True
        while self.is_running:
            self._get_gui_data()
            self._update_channels()
            time.sleep(0.02)

    def pause(self):
        """Pauses the wavemeter monitor"""
        self.is_running = False
        self.is_paused = True

    def resume(self):
        """Resumes the wavemeter monitor when paused"""
        self.is_paused = False

    def reconnect_gui(self):
        """ Reconnects to the GUI

        Should be called if the GUI connection has been lost, once a new GUI client with the same access parameters has
        been reinstantiated
        """
        self._gui_reconnect = True

    def zero_voltage(self, channel):
        """ Zeros the output voltage for this channel

        :param channel: (int) channel number to zero voltage of
        """

        # Get the relevant channel
        channel_list = self._get_channels()

        try:
            channel = self.channels[channel_list.index(channel)]
            channel.zero_voltage()

        # If the channel isn't monitored
        except KeyError:
            pass

    # Technical methods

    def _initialize_channel(self, index, channel):
        """Initializes a channel and outputs to the GUI

        Should only be called in the beginning of channel use to assign physical GUI widgets
        """

        # Get wavelength and initialize data arrays
        channel.initialize(
            wavelength=self.wlm_client.get_wavelength(channel.number),
            display_pts=self.display_pts
        )

        # Calculate indices for various gui widget defaults. This is GUI specific
        if channel.voltage is None:
            plot_multiplier = 2
            scalar_multiplier = 4
        else:
            plot_multiplier = 1
            scalar_multiplier = 2

        # Try to send data to the GUI
        try:
            self._gui_connected = True

            # First, clear the plot in case it was in use by some previous process
            self.gui.clear_plot(
                plot_widget=self._graph_widgets[plot_multiplier * (index + channel.plot_widget_offset)]
            )

            # Clear voltage if relevant
            if channel.voltage is not None:

                # First clear the plot
                self.gui.clear_plot(
                    plot_widget=self._graph_widgets[plot_multiplier * (index + channel.plot_widget_offset) + 1]
                )

            # Assign GUI + curves
            self.gui.assign_plot(
                plot_widget=self._graph_widgets[plot_multiplier * (index + channel.plot_widget_offset)],
                plot_label=channel.name,
                legend_widget=self._legend_widgets[plot_multiplier * (index + channel.plot_widget_offset)]
            )
            self.gui.assign_curve(
                plot_label=channel.name,
                curve_label=channel.curve_name
            )

            # Numeric label for laser frequency
            self.gui.assign_scalar(
                scalar_widget=self._number_widgets[scalar_multiplier * (index + channel.plot_widget_offset)],
                scalar_label=channel.name
            )

            # Only initialize setpoint plot if it is provided, since we don't want to clutter the screen
            if channel.setpoint is not None:
                self.gui.assign_curve(
                    plot_label=channel.name,
                    curve_label=channel.setpoint_name
                )

            # Numeric label for setpoint
            self.gui.assign_scalar(
                scalar_widget=self._number_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 1],
                scalar_label=channel.setpoint_name
            )

            # Assign lock and error boolean widgets
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[scalar_multiplier * (index + channel.plot_widget_offset)],
                scalar_label=channel.lock_name
            )
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 1],
                scalar_label=channel.error_name
            )

            # Assign pushbutton for clearing data
            self.gui.assign_event_button(
                event_widget=self._event_widgets[plot_multiplier * (index + channel.plot_widget_offset)],
                event_label=channel.name
            )

            # Assign voltage if relevant
            if channel.voltage is not None:

                # Now reassign it
                self.gui.assign_plot(
                    plot_widget=self._graph_widgets[plot_multiplier * (index + channel.plot_widget_offset) + 1],
                    plot_label=channel.aux_name,
                    legend_widget=self._legend_widgets[plot_multiplier * (index + channel.plot_widget_offset) + 1]
                )
                self.gui.assign_curve(
                    plot_label=channel.aux_name,
                    curve_label=channel.voltage_curve
                )
                self.gui.assign_curve(
                    plot_label=channel.aux_name,
                    curve_label=channel.error_curve
                )

                # Display scalars as well
                self.gui.assign_scalar(
                    scalar_widget=self._number_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 2],
                    scalar_label=channel.voltage_curve
                )
                self.gui.assign_scalar(
                    scalar_widget=self._number_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 3],
                    scalar_label=channel.error_curve
                )

                # Change label text for voltage
                self.gui.assign_label(
                    label_widget=self._label_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 2],
                    label_label=channel.voltage_curve
                )
                self.gui.assign_label(
                    label_widget=self._label_widgets[scalar_multiplier * (index + channel.plot_widget_offset) + 3],
                    label_label=channel.error_curve
                )

        # Handle GUI disconnection error
        except EOFError:

            # Mark that GUI has been disconnected and notify the user, but don't stop the script
            self._gui_connected = False
            print('GUI disconnected')

        # Handle case where we run out of GUI elements
        except IndexError:
            print("Sorry, there's no more room in this GUI!")

        # Handle case where we tried to assign some GUI widget that didn't exist
        except AttributeError:
            print('Incorrect GUI widget name - check .ui file in QtDesigner for widget names')

    def _update_channels(self):
        """ Updates all channels + displays

        Called continuously inside run() method to refresh WLM data and output on GUI
        """

        for channel in self.channels:

            # Update data with the new wavelength
            channel.update(self.wlm_client.get_wavelength(channel.number))

            # Try to update plots if we have a GUI connected
            if self._gui_connected:
                try:
                    self.gui.set_curve_data(
                        data=channel.data,
                        plot_label=channel.name,
                        curve_label=channel.curve_name
                    )
                    self.gui.set_scalar(
                        value=channel.data[-1],
                        scalar_label=channel.name
                    )

                    # Update setpoints if necessary
                    if channel.setpoint is not None:
                        self.gui.set_curve_data(
                            data=channel.sp_data,
                            plot_label=channel.name,
                            curve_label=channel.setpoint_name
                        )

                        # Update the setpoint to GUI directly if it has been changed
                        if channel.setpoint_override:

                            # Tell GUI to pull data provided by script and overwrite direct GUI input
                            self.gui.activate_scalar(
                                scalar_label=channel.setpoint_name
                            )
                            self.gui.set_scalar(
                                value=channel.setpoint,
                                scalar_label=channel.setpoint_name
                            )

                        # Otherwise, tell GUI to stop updating from script and accept direct GUI input
                        else:
                            self.gui.deactivate_scalar(
                                scalar_label=channel.setpoint_name
                            )

                    # Set lock and error booleans
                    if channel.setpoint is not None:

                        # If the lock has been updated, override the GUI
                        if channel.lock_override:
                            self.gui.activate_scalar(
                                scalar_label=channel.lock_name
                            )
                            self.gui.set_scalar(
                                value=channel.lock,
                                scalar_label=channel.lock_name
                            )

                        # Otherwise, enable GUI input
                        else:
                            self.gui.deactivate_scalar(
                                scalar_label=channel.lock_name
                            )

                        # Set the error boolean (true if the lock is active and we are outside the error threshold)
                        if channel.lock and np.abs(channel.data[-1] - channel.setpoint) > self.threshold:
                            self.gui.set_scalar(
                                value=True,
                                scalar_label=channel.error_name
                            )
                        else:
                            self.gui.set_scalar(
                                value=False,
                                scalar_label=channel.error_name
                            )

                    # Otherwise just set everything false, since we don't have a setpoint
                    else:
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.lock_name
                        )
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.error_name
                        )

                    # Now update lock + voltage plots + scalars if relevant
                    if channel.voltage is not None:
                        self.gui.set_curve_data(
                            data=channel.voltage,
                            plot_label=channel.aux_name,
                            curve_label=channel.voltage_curve
                        )
                        self.gui.set_curve_data(
                            data=channel.error,
                            plot_label=channel.aux_name,
                            curve_label=channel.error_curve
                        )
                        self.gui.set_scalar(
                            value=channel.voltage[-1],
                            scalar_label=channel.voltage_curve
                        )
                        self.gui.set_scalar(
                            value=channel.error[-1],
                            scalar_label=channel.error_curve
                        )

                        # Update labels, if desired
                        if not channel.labels_updated:
                            self.gui.set_label(
                                text='Voltage',
                                label_label=channel.voltage_curve
                            )
                            self.gui.set_label(
                                text='Lock Error',
                                label_label=channel.error_curve
                            )
                            channel.label_updated = True

                # Handle case that GUI crashes and client fails to connect to server
                except EOFError:
                    self._gui_connected = False
                    print('GUI disconnected')

                # Handle case where plot assignment has not been completed yet
                except KeyError:
                    pass

            # If GUI is not connected, check if we should try reconnecting to the GUI
            elif self._gui_reconnect:

                try:
                    self._gui_connected = True
                    self.gui.connect()

                    # Reinitialize channels to new GUI
                    self.initialize_channels()

                    # Manually update the GUI for a while so we don't change the setpoints
                    for i in range(100):
                        try:
                            channel.setpoint_override = True
                            channel.lock_override = True
                            self.gui.activate_scalar(scalar_label=channel.setpoint_name)
                            self.gui.activate_scalar(scalar_label=channel.lock_name)
                            self.gui.set_scalar(
                                value=channel.setpoint,
                                scalar_label=channel.setpoint_name
                            )
                            self.gui.set_scalar(
                                value=channel.lock,
                                scalar_label=channel.lock_name
                            )
                            self._update_channels()
                        except KeyError:
                            pass
                    print('GUI reconnected')
                except ConnectionRefusedError:
                    self._gui_connected = False
                    print('GUI reconnection failed')
                self._gui_reconnect = False

    def _get_gui_data(self):
        """ Updates setpoint and lock parameters with data pulled from GUI

        Does not overwrite the script setpoints and locks, but stores the GUI values for comparison based on context.
        See Channel.update() method for behavior on how script chooses whether to use internal values or GUI values
        """
        for channel in self.channels:

            # Pull the current value from the GUI
            if channel.setpoint is not None and self._gui_connected:
                try:
                    channel.gui_setpoint = self.gui.get_scalar(scalar_label=channel.setpoint_name)
                    channel.gui_lock = self.gui.get_scalar(scalar_label=channel.lock_name)

                # In case connection is lost
                except EOFError:
                    self._gui_connected = False
                    print('GUI disconnected')

                    pass
                # In case GUI is not configured
                except KeyError:
                    pass

            # Check pushbuttons and apply action if necessary
            try:
                if self._gui_connected and self.gui.was_button_pressed(event_label=channel.name):
                    self.clear_channel(channel=channel.number)

            # In case connection is lost
            except EOFError:
                self._gui_connected = False
                print('GUI disconnected')
                pass

            # In case GUI is not configured
            except KeyError:
                pass

    def _get_channels(self):
        """ Returns all active channel numbers

        Usually used for checking whether a newly input channel has already been assigned to the script

        :return: (list) all active channel numbers
        """

        channel_list = []
        for channel in self.channels:
            channel_list.append(channel.number)
        return channel_list


class Service(ServiceBase):
    """ A service to enable external updating of WlmMonitor parameters """

    def exposed_update_parameters(self, params_pickle):

        params = pickle.loads(params_pickle)
        return self._module.update_parameters(params)

    def exposed_clear_channel(self, channel):
        return self._module.clear_channel(channel)

    def exposed_reconnect_gui(self):
        return self._module.reconnect_gui()

    def exposed_zero_voltage(self, channel):
        return self._module.zero_voltage(channel)

    def exposed_pause(self):

        if isinstance(self._module, list):
            for module in self._module:
                module.pause()
            return 0

        else:
            return self._module.pause()

    def exposed_resume(self):
        return self._module.resume()


class Client(ClientBase):

    def update_parameters(self, params):

        params_pickle = pickle.dumps(params)
        return self._service.exposed_update_parameters(params_pickle)

    def clear_channel(self, channel):
        return self._service.exposed_clear_channel(channel)

    def zero_voltage(self, channel):
        return self._service.exposed_zero_voltage(channel)

    def reconnect_gui(self):
        return self._service.exposed_reconnect_gui()

    def pause(self):

        return self._service.exposed_pause()

    def resume(self):
        return self._service.exposed_resume()


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
