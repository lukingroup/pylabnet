from pylabnet.scripts.pid import PID
import numpy as np
import time
import copy


# Static methods

def generate_widgets():
    """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""
    graphs, legends, numbers, booleans, labels = [], [], [], [], []

    for i in range(4):
        graphs.append('graph_widget_'+str(i+1))
        legends.append('legend_widget_'+str(i+1))
        numbers.append('number_widget_'+str(i+1))
        booleans.append('boolean_widget_'+str(i+1))
        labels.append('label_'+str(i+1))
    for i in range(4, 8):
        numbers.append('number_widget_' + str(i + 1))
        booleans.append('boolean_widget_' + str(i + 1))
        labels.append('label_'+str(i+1))
    return graphs, legends, numbers, booleans, labels


class WlmMonitor:

    # Assign widget names based on .gui file. This line works for wavemetermonitor_4ch.ui
    _graph_widgets, _legend_widgets, _number_widgets, _boolean_widgets, _label_widgets = generate_widgets()

    def __init__(self, wlm_client=None, ao_clients=None, display_pts=5000, threshold=0.0002):
        """
        Instantiates WlmMonitor script object for monitoring wavemeter

        :param wlm_client: (obj) instance of wavemeter client
        :param ao_clients: (dict) dictionary of AO client objects with keys to identify. Exmaple:
            {'ni_usb_1': nidaqmx_usb_client_1, 'ni_usb_2': nidaqmx_usb_client_2, 'ni_pxi_multi': nidaqmx_pxi_client}
        :param error_monitor: (bool) whether or not to monitor error + voltage on a separate plot
        :param display_pts: (int) number of points to display on plot
        :param threshold: (float) threshold in THz for lock error signal
        """

        self.channels = []
        self.gui = None
        self.is_running = False
        self.is_paused = False
        self._gui_connected = False
        self._gui_reconnect = False
        self.wlm_client = wlm_client
        self.ao_clients = ao_clients
        self.display_pts = display_pts
        self.threshold = threshold

    def assign_gui(self, gui_client):
        """ Assigns a GUI client to the WlmMonitor

        :param gui_client: (obj) instance of GUI client
        """

        self.gui = gui_client

    def assign_wlm(self, wlm_client):
        """
        Assigns the wlm Client to the WlmMonitor module

        :param wlm_client: (obj) instance of Client of High-Finesse wavemeter
        """

        self.wlm_client = wlm_client

    def assign_channel(self, channel_params):
        """
        Instantiates a new channel with given parameters and assigns it to the WlmMonitor

        :param channel_params: (dict) dictionary containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'PID': {'p': 1, 'i': 0.1, 'd': 0}, 'AO': {'client':'nidaqmx_client', 'channel': 'ao1'},
             'voltage_monitor': True}
        """
        self.channels.append(Channel(channel_params, self.ao_clients))

    def set_parameters(self, all_parameters):
        """
        Assigns all channels (for convenience in a single call from the notebook). Overwrites all parameters, not just
        given ones.

        :param all_parameters: (list) list of all dictionaries of channel parameters. For dictionary example/structure,
            see the assign_channel method
        """

        for channel_params in all_parameters:
            self.assign_channel(channel_params=channel_params)

    def update_parameters(self, parameters):
        """
        Updates only the parameters given. Can be used in the middle of the script operation

        :param parameters: (list) list of dictionaries, see assign_channel() for details
        """

        for parameter in parameters:

            # Only proceed if a channel number is given
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
                            self.gui.force_update()
                            channel.setpoint = parameter['setpoint']
                            channel.pid.set_parameters(setpoint=channel.setpoint)
                            channel.initialize_sp_data()

                        # If the setpoint existed and is now removed, delete the plot item
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

                            # Mark that we should override setpoint
                            channel.setpoint_override = True

                    if 'lock' in parameter:
                        channel.lock = parameter['lock']
                        channel.lock_override = True
                    if 'memory' in parameter:
                        channel.memory = parameter['memory']
                    if 'PID' in parameter:
                        channel.pid.set_parameters(
                            p=parameter['PID']['p'],
                            i=parameter['PID']['i'],
                            d=parameter['PID']['d'],
                        )
                    if 'AO' in parameter and self.ao_clients is not None:
                        # Convert AO from string to object using lookup
                        try:
                            channel.ao = {
                                'client': self.ao_clients[parameter['AO']['client']],
                                'channel': parameter['AO']['channel']
                            }
                        except KeyError:
                            channel.ao = None

                # Otherwise, it is a new channel so we should add it
                else:
                    self.channels.append(Channel(parameter))
                    self._initialize_channel(
                        index=len(self.channels)-1,
                        channel=self.channels[-1]
                    )

    def initialize_channels(self):
        """Initializes all channels and outputs to the GUI"""

        for index, channel in enumerate(self.channels):
            self._initialize_channel(index, channel)

    def run(self):
        """Runs the WlmMonitor"""

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
        """Resumes the wavemeter monitor by raising a flag"""
        self.is_paused = False

    def reconnect_gui(self):
        self._gui_reconnect = True

    def zero_voltage(self, channel):
        """
        Zeros the voltage for this channel

        :param channel: (int) channel number to zero voltage of
        """

        # Get the relevant channel
        channel_list = self._get_channels()
        channel = self.channels[channel_list.index(channel)]

        # Zero voltage for this channel
        channel.zero_voltage()

    # Technical methods

    def _initialize_channel(self, index, channel):
        """Initializes a channel"""

        # Get wavelength and initialize data
        channel.initialize(
            wavelength=self.wlm_client.get_wavelength(channel.number),
            display_pts=self.display_pts
        )

        # Calculate indices for various gui widget defaults
        if channel.voltage is None:
            plot_multiplier = 2
            scalar_multiplier = 4
        else:
            plot_multiplier = 1
            scalar_multiplier = 2

        # Try to send data to the GUI
        try:
            self._gui_connected = True

            # Clear the plot
            self.gui.clear_plot(
                plot_widget=self._graph_widgets[plot_multiplier*(index + channel.plot_widget_offset)]
            )

            # Assign GUI + curves
            self.gui.assign_plot(
                plot_widget=self._graph_widgets[plot_multiplier*(index + channel.plot_widget_offset)],
                plot_label=channel.name,
                legend_widget=self._legend_widgets[plot_multiplier*(index + channel.plot_widget_offset)]
            )
            self.gui.assign_curve(
                plot_label=channel.name,
                curve_label=channel.curve_name
            )

            # Numeric label
            self.gui.assign_scalar(
                scalar_widget=self._number_widgets[scalar_multiplier*(index + channel.plot_widget_offset)],
                scalar_label=channel.name
            )

            # Only initialize setpoint plot if it is provided
            if channel.setpoint is not None:
                self.gui.assign_curve(
                    plot_label=channel.name,
                    curve_label=channel.setpoint_name
                )

            # Numeric label for setpoint
            self.gui.assign_scalar(
                scalar_widget=self._number_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 1],
                scalar_label=channel.setpoint_name
            )

            # Assign lock and error boolean widgets
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[scalar_multiplier*(index + channel.plot_widget_offset)],
                scalar_label=channel.lock_name
            )
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 1],
                scalar_label=channel.error_name
            )

            # Assign voltage if relevant
            if channel.voltage is not None:
                self.gui.assign_plot(
                    plot_widget=self._graph_widgets[plot_multiplier*(index + channel.plot_widget_offset) + 1],
                    plot_label=channel.aux_name,
                    legend_widget=self._legend_widgets[plot_multiplier*(index + channel.plot_widget_offset) + 1]
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
                    scalar_widget=self._number_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 2],
                    scalar_label=channel.voltage_curve
                )
                self.gui.assign_scalar(
                    scalar_widget=self._number_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 3],
                    scalar_label=channel.error_curve
                )

                # Change label text for voltage
                self.gui.assign_label(
                    label_widget=self._label_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 2],
                    label_label=channel.voltage_curve
                )
                self.gui.assign_label(
                    label_widget=self._label_widgets[scalar_multiplier*(index + channel.plot_widget_offset) + 3],
                    label_label=channel.error_curve
                )

            self.gui.force_update()

        except EOFError:
            self._gui_connected = False
            print('GUI disconnected')
        except IndexError:
            print("Sorry, there's no more room in this GUI!")
            raise
        except AttributeError:
            print('Incorrect GUI widget name - check .ui file in QtDesigner for widget names')
            raise

    def _update_channels(self):
        """Updates all channels + displays"""

        for channel in self.channels:

            # Update data
            channel.update(self.wlm_client.get_wavelength(channel.number))

            # Try to update plots
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
                        if channel.setpoint_override:
                            # Tell GUI to pull data provided by script
                            self.gui.activate_scalar(
                                scalar_label=channel.setpoint_name
                            )
                            self.gui.set_scalar(
                                value=channel.setpoint,
                                scalar_label=channel.setpoint_name
                            )
                        else:
                            # Tell GUI to stop updating from script
                            self.gui.deactivate_scalar(
                                scalar_label=channel.setpoint_name
                            )
                    else:
                        self.gui.set_scalar(
                            value=0,
                            scalar_label=channel.setpoint_name
                        )

                    # Set lock and error booleans
                    if channel.setpoint is not None:
                        if channel.lock_override:
                            self.gui.activate_scalar(
                                scalar_label=channel.lock_name
                            )
                            self.gui.set_scalar(
                                value=channel.lock,
                                scalar_label=channel.lock_name
                            )
                        else:
                            self.gui.deactivate_scalar(
                                scalar_label=channel.lock_name
                            )
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

                    # Otherwise just set everything false
                    else:
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.lock_name
                        )
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.error_name
                        )

                    # Now update lock + voltage plots + scalars
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

                    # Update labels, if relevant
                    if not channel.labels_updated:
                        self.gui.set_label(
                            text=channel.voltage_curve,
                            label_label=channel.voltage_curve
                        )
                        self.gui.set_label(
                            text=channel.error_curve,
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

            # Check if we should try reconnecting to the GUI
            elif self._gui_reconnect:
                try:
                    self._gui_connected = True
                    self.gui.connect()
                except ConnectionRefusedError:
                    self._gui_connected = False
                    print('GUI reconnection failed')
                self._gui_reconnect = False

                self.initialize_channels()

    def _get_gui_data(self):
        """ Updates setpoint and lock parameters with data pulled from GUI"""
        for channel in self.channels:

            # Pull the current value from the GUI
            if channel.setpoint is not None:
                try:
                    channel.gui_setpoint = self.gui.get_scalar(scalar_label=channel.setpoint_name)
                    channel.gui_lock = self.gui.get_scalar(scalar_label=channel.lock_name)

                # In case connection is lost
                except EOFError:
                    pass
                # In case GUI is not configured
                except KeyError:
                    pass

    def _get_channels(self):
        """
        Returns all active channel numbers

        :return: (list) all active channel numbers
        """

        channel_list = []
        for channel in self.channels:
            channel_list.append(channel.number)
        return channel_list


class Channel:
    """Object containing all information regarding a single wavemeter channel"""

    # Set acceptable voltage range for laser modulation
    _min_voltage = -10
    _max_voltage = 10
    _gain = 1000

    def __init__(self, channel_params, ao_clients=None):
        """
        Initializes all parameters given, sets others to default. Also sets up some defaults + placeholders for data

        :param channel_params: (dict) Dictionary of channel parameters (see above for examples)
        :param ao_clients: (dict, optional) Dictionary containing AO clients tying a keyname string to the actual client
        """

        # Set channel parameters
        self.ao_clients = ao_clients
        self.ao = None
        self.voltage = None
        self.current_voltage = 0
        self.setpoint = None
        self.error = None
        self.labels_updated = False
        self.setpoint_override = True
        self.lock_override = True
        self.gui_setpoint = 0
        self.gui_lock = False
        self.lock = False
        self.prev_gui_lock = None
        self.prev_gui_setpoint = None

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

        self.data = np.ones(display_pts)*wavelength

        if self.setpoint is not None:
            self.sp_data = np.ones(display_pts)*self.setpoint

        # Initialize voltage and error
        if self.voltage is not None:
            self.voltage = np.ones(display_pts)*self.pid.cv

            # Check that setpoint is reasonable, otherwise set error to 0
            if self.setpoint is None:
                self.error = np.zeros(display_pts)
            else:
                self.error = np.ones(display_pts)*(wavelength - self.setpoint)

    def initialize_sp_data(self, display_pts=5000):
        if self.setpoint is not None:
            self.sp_data = np.ones(display_pts)*self.setpoint

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
        self.pid.set_pv(pv=self.data[len(self.data)-self.memory:])
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
                    if self._min_voltage <= self.current_voltage + self.pid.cv*self._gain <= self._max_voltage:
                        self.current_voltage += self.pid.cv*self._gain
                    elif self.current_voltage + self.pid.cv*self._gain < self._min_voltage:
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
            self.error = np.append(self.error[1:], self.pid.error*self._gain)

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
        """
        Sets all internal channel parameters to input. If parameters are not given, they are overwritten to defaults

        :param channel_params: (dict) dictionary containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'PID': {'p': 1, 'i': 0.1, 'd': 0}, 'AO': {'client': 'nidaqmx_client', 'channel': 'ao1'}}
        """

        # Initialize all given attributes, otherwise initialize defaults
        if 'channel' in channel_params:
            self.number = channel_params['channel']
        else:
            self.number = 1

        if 'name' in channel_params:
            self.name = channel_params['name']
        else:
            # Initialize random channel name if not given
            self.name = 'Channel '+str(np.random.randint(1000000))
        self.curve_name = self.name + ' Frequency'
        self.lock_name = self.name + ' Lock'
        self.error_name = self.name + ' Error'

        if 'setpoint' in channel_params:
            self.setpoint = channel_params['setpoint']
        else:
            self.setpoint = None
        self.setpoint_name = self.name + ' Setpoint'

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
                self.ao = None
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
        else:
            self.voltage = None

        if 'plot_widget' in channel_params:
            self.plot_widget_offset = channel_params['plot_widget']
        else:
            self.plot_widget_offset = 0
