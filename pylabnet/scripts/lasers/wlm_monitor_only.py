from pylabnet.scripts.pid import PID
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (unpack_launcher, create_server,
                                           load_config, get_gui_widgets, get_legend_from_graphics_view, add_to_legend, find_client,
                                           load_script_config, get_ip)
from pylabnet.utils.logging.logger import LogClient, LogHandler

import numpy as np
import time
import copy
import pickle
import pyqtgraph as pg


class WlmMonitor:
    """ A script class for monitoring and locking lasers based on the wavemeter """

    def __init__(self, wlm_client, logger_client, gui='wavemeter_monitor_only', display_pts=5000, threshold=0.0002, port=None, params=None, three_lasers=False):
        """ Instantiates WlmMonitor script object for monitoring wavemeter

        :param wlm_client: (obj) instance of wavemeter client
        :param gui_client: (obj) instance of GUI client.
        :param logger_client: (obj) instance of logger client.
        :param ao_clients: (dict, optional) dictionary of ao client objects with keys to identify. Exmaple:
            {'ni_usb_1': nidaqmx_usb_client_1, 'ni_usb_2': nidaqmx_usb_client_2, 'ni_pxi_multi': nidaqmx_pxi_client}
        :param display_pts: (int, optional) number of points to display on plot
        :param threshold: (float, optional) threshold in THz for lock error signal
        :param port: (int) port number for update server
        :param params: (dict) see set_parameters below for details
        :three_lasers: (bool) If three lasers are in use (instead of 2)
        """
        self.channels = []

        if three_lasers:
            gui = 'wavemeter_monitor_3lasers'

        self.wlm_client = wlm_client
        self.display_pts = display_pts
        self.threshold = threshold
        self.log = LogHandler(logger_client)

        # Instantiate gui
        self.gui = Window(
            gui_template=gui,
            host=get_ip(),
            port=port,
            log=self.log
        )

        # Setup stylesheet.
        self.gui.apply_stylesheet()

        # Make fullscreen
        self.gui.showFullScreen()

        if three_lasers:
            self.widgets = get_gui_widgets(
                gui=self.gui,
                freq=3, sp=3, rs=3, lock=3, error_status=3, graph=6, legend=6, clear=6,
                zero=6, voltage=3, error=3
            )
        else:
            self.widgets = get_gui_widgets(
                gui=self.gui,
                freq=2, graph=2, legend=2, clear=2
            )

        # Set parameters
        self.set_parameters(**params)

        # Configure plots
        # Get actual legend widgets
        self.widgets['legend'] = [get_legend_from_graphics_view(legend) for legend in self.widgets['legend']]

        self.widgets['curve'] = []
        self.initialize_channels()

        for channel in self.channels:
            self.update_parameters(dict(
                channel=channel.number,
                setpoint=channel.data[-1]
            ))

    def toogle_laser(self):
        self.self.widgets['curve'][0].hide()

    def set_parameters(self, channel_params):
        """ Instantiates new channel objects with given parameters and assigns them to the WlmMonitor

        Note: parameters for a channel that has already been assigned can be set or updated later using the
        update_parameters() method via an update client in a separate python process.

        :param channel_params: (list) of dictionaries containing all parameters. Example of full parameter set:
            {'channel': 1, 'name': 'Velocity', 'setpoint': 406.7, 'lock':True, 'memory': 20,
             'pid': {'p': 1, 'i': 0.1, 'd': 0}, 'ao': {'client':'nidaqmx_client', 'channel': 'ao1'}}

            In more detail:
            - 'channel': should be from 1-8 for the High-Finesse Wavemeter (with switch) and should ALWAYS be provided,
                as a reference so that we know which channel to assign all the other parameters to
            - 'name': a string that can just be provided once and is used as a user-friendly name for the channel.
                Initializes to 'Channel X' where X is a random integer if not provided
            - 'setpoint': setpoint for this channel.
            - 'lock': boolean that tells us whether or not to turn on the lock. Ignored if setpoint is None. Default is
                False.
            - 'memory': Number of points for integral memory of pid (history of the integral). Default is 20.
            - 'pid': dict containing pid parameters. Uses the pylabnet.scripts.pid module. By default instantiates the
                default PID() object.
            - 'ao': dict containing two elements: 'client' which is a string that is the name of the ao client to use
                for locking. This should match up with a key in self.ao_clients. 'channel'is an identifier for which
                analog output to use for this channel. By default it is set to None and no active locking is performed
        """

        # Check if it is only a single channel
        if type(channel_params) is dict:
            channel_params = [channel_params]

        # Initialize each channel individually
        for channel_param_set in channel_params:
            self.channels.append(Channel(channel_param_set, log=self.log))

    def update_parameters(self, parameters):
        """ Updates only the parameters given. Can be used in the middle of the script operation via an update client.

        :param parameters: (list) list of dictionaries, see set_parameters() for details
        """

        if not isinstance(parameters, list):
            parameters = [parameters]

        for parameter in parameters:

            # Make sure a channel is given
            if 'channel' in parameter:

                # Check if it is a channel that is already logged
                channel_list = self._get_channels()
                if parameter['channel'] in channel_list:

                    # Find index of the desired channel
                    index = channel_list.index(parameter['channel'])
                    channel = self.channels[channel_list.index(parameter['channel'])]

                    # Set all other parameters for this channel
                    if 'name' in parameter:
                        channel.name = parameter['name']

                    if 'setpoint' in parameter:

                        # self.widgets['sp'][index].setValue(parameter['setpoint'])
                        # channel.setpoint = parameter['setpoint']

                        # Mark that we should override GUI setpoint, since it has been updated by the script
                        channel.setpoint_override = parameter['setpoint']

                    if 'lock' in parameter:

                        self.widgets['lock'][index].setChecked(parameter['lock'])
                        # channel.lock = parameter['lock']

                        # Mark that we should override the GUI lock since it has been updated by the script
                        # channel.lock_override = True

                    if 'memory' in parameter:
                        channel.memory = parameter['memory']
                    if 'pid' in parameter:
                        channel.pid.set_parameters(
                            p=parameter['pid']['p'],
                            i=parameter['pid']['i'],
                            d=parameter['pid']['d'],
                        )

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

        :param channel: Channel object to clear
        """

        try:
            channel.initialize(channel.data[-1])

        # If the channel isn't monitored
        except:
            self.log.warn('Could not clear channel')

    def clear_all(self):
        """ Clears all channels """

        for channel in self.channels:
            self.clear_channel(channel)

    def run(self):
        """Runs the WlmMonitor

        Can be stopped using the pause() method
        """

        self._update_channels()
        self.gui.force_update()

    def go_to(self, channel, value, step_size, hold_time):
        """ Sends laser to a setpoint value gradually

        :param channel: (int) channel number on wavemeter
        :param value: (float) value to set laser frequency to
        :param step_size: (float) step size in THz for laser freq steps
        :param hold_time: (float) time in seconds to wait between steps
        """

        # Index of channel
        physical_channel = self.channels[self._get_channels().index(channel)]

        # Generate array of points to go to
        traverse = np.linspace(physical_channel.setpoint, value, int((value - physical_channel.setpoint) / step_size))

        for frequency in traverse:
            self.set_parameters([dict(
                channel=channel,
                setpoint=frequency
            )])
            time.sleep(hold_time)

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

        # Create curves
        # frequency
        self.widgets['curve'].append(self.widgets['graph'][index].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        ))
        add_to_legend(
            legend=self.widgets['legend'][index],
            curve=self.widgets['curve'][index],
            curve_name=channel.curve_name
        )

        # Clear data
        self.widgets['clear'][index].clicked.connect(
            lambda: self.clear_channel(channel)
        )

    def _update_channels(self):
        """ Updates all channels + displays

        Called continuously inside run() method to refresh WLM data and output on GUI
        """

        for index, channel in enumerate(self.channels):

            # Update data with the new wavelength
            channel.update(self.wlm_client.get_wavelength(channel.number))

            # Update frequency
            self.widgets['curve'][index].setData(channel.data)
            self.widgets['freq'][index].setValue(channel.data[-1])

    def _get_channels(self):
        """ Returns all active channel numbers

        Usually used for checking whether a newly input channel has already been assigned to the script

        :return: (list) all active channel numbers
        """

        channel_list = []
        for channel in self.channels:
            channel_list.append(channel.number)
        return channel_list

    def get_wavelength(self, channel):
        # Index of channel
        physical_channel = self.channels[self._get_channels().index(channel)]
        return self.wlm_client.get_wavelength(physical_channel.number)


class Service(ServiceBase):
    """ A service to enable external updating of WlmMonitor parameters """

    def exposed_update_parameters(self, params_pickle):

        params = pickle.loads(params_pickle)
        return self._module.update_parameters(params)

    def exposed_clear_channel(self, channel):
        return self._module.clear_channel(channel)

    def exposed_reconnect_gui(self):
        return self._module.reconnect_gui()

    def exposed_pause(self):

        if isinstance(self._module, list):
            for module in self._module:
                module.pause()
            return 0

        else:
            return self._module.pause()

    def exposed_resume(self):
        return self._module.resume()

    def exposed_go_to(self, channel, value, step_size, hold_time):
        return self._module.go_to(channel, value, step_size, hold_time)

    def exposed_get_wavelength(self, channel):
        return self._module.get_wavelength(channel)


class Client(ClientBase):

    def update_parameters(self, params):

        params_pickle = pickle.dumps(params)
        return self._service.exposed_update_parameters(params_pickle)

    def get_wavelength(self, channel):
        return self._service.exposed_get_wavelength(channel)

    def clear_channel(self, channel):
        return self._service.exposed_clear_channel(channel)

    def reconnect_gui(self):
        return self._service.exposed_reconnect_gui()

    def pause(self):

        return self._service.exposed_pause()

    def resume(self):
        return self._service.exposed_resume()

    def go_to(self, channel, value, step_size=0.001, hold_time=0.1):
        """ Sends laser to a setpoint value gradually

        :param channel: (int) channel number on wavemeter
        :param value: (float) value to set laser frequency to
        :param step_size: (float) step size in THz for laser freq steps
        :param hold_time: (float) time in seconds to wait between steps
        """

        return self._service.exposed_go_to(channel, value, step_size, hold_time)


class Channel:
    """Object containing all information regarding a single wavemeter channel"""

    def __init__(self, channel_params, log: LogHandler = None):
        """
        Initializes all parameters given, sets others to default. Also sets up some defaults + placeholders for data

        :param channel_params: (dict) Dictionary of channel parameters (see WlmMonitor.set_parameters() for details)
        :param ao_clients: (dict, optional) Dictionary containing ao clients tying a keyname string to the actual client
        :param log: (LogHandler) instance of LogHandler for logging metadata
        """

        # Set channel parameters to default values
        self.log = log
        self.ao = None  # Dict with client name and channel for ao to use
        self.setpoint = None
        self.lock = False
        self.error = None  # Array of error values, used for plotting/monitoring lock error
        self.labels_updated = False  # Flag to check if we have updated all labels
        self.setpoint_override = 0  # Flag to check if setpoint has been updated + GUI should be overridden
        # self.lock_override = True  # Flag to check if lock has been updated + GUI should be overridden
        self.gui_setpoint = 0  # Current GUI setpoint
        self.gui_lock = False  # Current GUI lock boolean
        self.prev_gui_lock = None  # Previous GUI lock boolean
        self.prev_gui_setpoint = None  # Previous GUI setpoint
        self._gain = None

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

        self.sp_data = np.ones(display_pts) * self.data[-1]
        self.setpoint = self.data[-1]
        # self.setpoint_override = True

        # self.lock_override = True

    def initialize_sp_data(self, display_pts=5000):
        self.sp_data = np.ones(display_pts) * self.data[-1]

    def update(self, wavelength):
        """
        Updates the data, setpoints, and all locks

        :param wavelength: (float) current wavelength
        """

        self.data = np.append(self.data[1:], wavelength)

        # Pick which setpoint to use
        # If the setpoint override is on, this means we need to try and set the GUI value to self.setpoint
        # if self.setpoint_override:

        #     # Check if the GUI has actually caught up
        #     if self.setpoint == self.gui_setpoint:
        #         self.setpoint_override = False

        #     # Otherwise, the GUI still hasn't implemented the setpoint prescribed by update_parameters()

        # # If setpoint override is off, this means the GUI caught up to our last update_parameters() call, and we
        # # should refrain from updating the value until we get a new value from the GUI
        # else:

        # Check if the GUI has changed, and if so, update the setpoint in the script to match
        if self.gui_setpoint != self.prev_gui_setpoint:
            self.setpoint = copy.deepcopy(self.gui_setpoint)
            metadata = {f'{self.name}_laser_setpoint': self.setpoint}
            self.log.update_metadata(**metadata)

            # Otherwise the GUI is static AND parameters haven't been updated so we don't change the setpoint at all

        # Store the latest GUI setpoint
        self.prev_gui_setpoint = copy.deepcopy(self.gui_setpoint)
        self.sp_data = np.append(self.sp_data[1:], self.setpoint)

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


def launch(**kwargs):
    """ Launches the WLM monitor + lock script """

    logger = kwargs['logger']
    config = load_script_config(
        script='wlm_monitor_ford',
        config=kwargs['config'],
        logger=logger
    )

    # TODO: Generalize this for n lasers.
    if config['num_lasers'] == 3:
        three_lasers = True
    else:
        three_lasers = False
    device_id = config['device_id']

    wavemeter_client = find_client(
        clients=kwargs['clients'],
        settings=config,
        client_type='high_finesse_ws7',
        logger=logger)

    channel_params = [p for p in config['channels'].values()]
    params = dict(channel_params=channel_params)

    # Instantiate Monitor script
    wlm_monitor = WlmMonitor(
        wlm_client=wavemeter_client,
        logger_client=logger,
        params=params,
        three_lasers=three_lasers
    )

    update_service = kwargs['service']
    update_service.assign_module(module=wlm_monitor)
    logger.update_data(data=dict(device_id=device_id))
    wlm_monitor.gui.set_network_info(port=kwargs['server_port'])

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        wlm_monitor.run()
