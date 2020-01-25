from pylabnet.scripts.pid import PID
import numpy as np
import time

from pylabnet.scripts.gui_configurators.configurator import GUIConfigurator


# Static methods

def generate_widgets():
    """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""

    graphs = ['graph_widget_{}'.format(i+1) for i in range(4)]
    legends = ['legend_widget_{}'.format(i+1) for i in range(4)]
    numbers = ['number_widget_{}'.format(i+1) for i in range(8)]
    booleans = ['boolean_widget_{}'.format(i+1) for i in range(8)]

    return graphs, legends, numbers, booleans


class WlmGUIConfigurator(GUIConfigurator):

    # Assign widget names based on .gui file. This line works for wavemetermonitor_4ch.ui
    _graph_widgets, _legend_widgets, _number_widgets, _boolean_widgets = generate_widgets()

    def __init__(self, wlm_client=None, display_pts=5000, threshold=0.0002):
        """
        Instantiates WlmMonitor script object for monitoring wavemeter

        :param wlm_client: (obj) instance of wavemeter client
        :param display_pts: (int) number of points to display on plot
        :param threshold: (float) threshold in THz for lock error signal
        """

        # Instanciate generic GUIConfigurator
        GUIConfigurator.__init__(self, client=None)

        self.channels = []
        self.display_pts = display_pts
        self.threshold = threshold

    def assign_channel(self, channel_params):
        """
        Instantiates a new channel with given parameters and assigns it to the WlmMonitor

        :param channel_params: (dict) dictionary containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'PID': {'p': 1, 'i': 0.1, 'd': 0}}
        """
        self.channels.append(Channel(channel_params))

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

                    if 'lock' in parameter:
                        channel.lock = parameter['lock']
                    if 'memory' in parameter:
                        channel.memory = parameter['memory']
                    if 'PID' in parameter:
                        channel.pid.set_parameters(
                            p=parameter['PID']['p'],
                            i=parameter['PID']['i'],
                            d=parameter['PID']['d'],
                        )

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

    def update_channels(self):
        """Updates the wavelength for each channel"""

        self._initialize_channels()
        for channel in self.channels:
            channel.update()

    def run(self):
        """Runs the WlmMonitor. Can also be used to resume after a pause"""

        self.is_running = True
        while self.is_running:
            self._update_channels()
            time.sleep(0.003)

    def pause(self):
        """Pauses the wavemeter monitor"""
        self.is_running = False

    def reconnect_gui(self):
        self._gui_reconnect = True

    # Technical methods

    def _initialize_channel(self, index, channel):
        """Initializes a channel"""

        # Get wavelength and initialize data
        channel.initialize(
            wavelength=self.wlm_client.get_wavelength(channel.number),
            display_pts=self.display_pts
        )

        # Try to send data to the GUI
        try:
            self._gui_connected = True

            # Assign GUI + curves
            self.gui.assign_plot(
                plot_widget=self._graph_widgets[index],
                plot_label=channel.name,
                legend_widget=self._legend_widgets[index]
            )
            self.gui.assign_curve(
                plot_label=channel.name,
                curve_label=channel.curve_name
            )

            # Numeric label
            self.gui.assign_scalar(
                scalar_widget=self._number_widgets[2 * index],
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
                scalar_widget=self._number_widgets[2 * index + 1],
                scalar_label=channel.setpoint_name
            )

            # Assign lock and error boolean widgets
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[2 * index],
                scalar_label=channel.lock_name
            )
            self.gui.assign_scalar(
                scalar_widget=self._boolean_widgets[2 * index + 1],
                scalar_label=channel.error_name
            )

            self.gui.force_update()

        except EOFError:
            self._gui_connected = False
            print('GUI disconnected')

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
                        self.gui.set_scalar(
                            value=channel.setpoint,
                            scalar_label=channel.setpoint_name
                        )
                    else:
                        self.gui.set_scalar(
                            value=0,
                            scalar_label=channel.setpoint_name
                        )

                    # Set lock and error booleans
                    if channel.setpoint is not None:
                        self.gui.set_scalar(
                            value=channel.lock,
                            scalar_label=channel.lock_name
                        )
                        if channel.lock and np.abs(channel.data[-1]-channel.setpoint) > self.threshold:
                            self.gui.set_scalar(
                                value=True,
                                scalar_label=channel.error_name
                            )
                        else:
                            self.gui.set_scalar(
                                value=False,
                                scalar_label=channel.error_name
                            )

                    # If the setpoint isn't given just set everything false
                    else:
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.lock_name
                        )
                        self.gui.set_scalar(
                            value=False,
                            scalar_label=channel.error_name
                        )

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

    def __init__(self, channel_params):
        """
        Initializes all parameters given, sets others to default. Also sets up some defaults + placeholders for data

        :param channel_params:
        """

        # Set channel parameters
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
            self.sp_data = np.append(self.sp_data[1:], self.setpoint)
        self.pid.set_parameters(setpoint=0 if self.setpoint is None else self.setpoint)

        # Implement lock
        if self.lock:
            # Set process variable
            self.pid.set_pv(pv=self.data[len(self.data)-self.memory:])
            # Set control variable
            self.pid.set_cv()

            # TODO: implement voltage

    def _overwrite_parameters(self, channel_params):
        """
        Sets all internal channel parameters to input. If parameters are not given, they are overwritten to defaults

        :param channel_params: (dict) dictionary containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'PID': {'p': 1, 'i': 0.1, 'd': 0}}
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
