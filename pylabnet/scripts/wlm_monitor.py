from pylabnet.gui.igui.iplot import SingleTraceFig, MultiTraceFig
from pylabnet.scripts.pid import PID
import numpy as np
import time


class WlmMonitor:
    """Script class for monitoring wavemeter"""

    def __init__(self, wlm_client=None):

        # Store wavemeter client
        if wlm_client is None:
            msg_str = "Please pass wavemeter client in order to instantiate WlmMonitor script."
            raise Exception(msg_str)

        self._wlm = wlm_client
        self._is_running = False
        self.channels = [None]
        self._x_axis = None
        self._data_length = 0
        self._display_length = 0
        self._update_rate = 0
        self._bin_by = 0

    def set_params(self, channels=None, update_rate=0.05, display_pts=1000, bin_by=5, memory=10):
        """
        Configures script parameters for wavemeter control
        
        :param channels: list of dictionaries containing channel information in the example structure:
            {"channel": 1, "setpoint": None, "lock": False, "PID":[0, 0, 0]}
        :param update_rate: how often to update the plot in seconds
            Note: this should be increased in order to avoid lagging in plot outputting
        :param display_pts: number of points to display on graph
        :param bin_by: number of wavemeter samples per display point
        :param memory: number of points to use for integral memory
        """

        self._bin_by = bin_by
        self._display_length = display_pts
        self._data_length = self._display_length * self._bin_by
        self._x_axis = np.arange(self._data_length)
        self._update_rate = update_rate

        # Initialize to default settings if nothing provided
        if channels is None:
            self.channels = [{
                "channel": 1,
                "setpoint": None,
                "lock": False
            }]
        else:
            self.channels = channels

        for channel in self.channels:

            # We need to configure the plot differently based on whether or not a setpoint is given
            if channel["setpoint"] is None:

                # Initialize plot with no setpoints
                channel["trace"] = SingleTraceFig(title_str="Channel {} Laser Monitor".format(channel["channel"]))

            else:

                # Initialize plot with setpoints
                channel["trace"] = MultiTraceFig(
                    title_str="Channel {} Laser Monitor".format(channel["channel"]),
                    ch_names=["Channel {} Frequency".format(channel["channel"]),
                              "Channel {} Setpoint".format(channel["channel"])],
                    legend_orientation='h'
                )

                # If a setpoint is given, configure PID to be an instance of PID class with desired parameters
                if "PID" in channel:
                    channel["PID"] = PID(
                        p=channel["PID"][0],
                        i=channel["PID"][1],
                        d=channel["PID"][2],
                        memory=memory,
                        setpoint=channel["setpoint"]
                    )

                # If PID parameters were not provided, but we have a setpoint, initialize PID to [0, 0, 0]
                else:
                    channel["PID"] = PID(
                        p=0,
                        i=0,
                        d=0,
                        memory=memory,
                        setpoint=channel["setpoint"]
                    )

                # Initialize lock monitor
                channel["error_monitor"] = SingleTraceFig(
                    title_str="Channel {} Lock Error Monitor".format(channel["channel"])
                )
                channel["error_monitor"].set_lbls(
                    x_str="Time (pts)",
                    y_str="Lock error (GHz)"
                )
                channel["voltage_monitor"] = SingleTraceFig(
                    title_str="Channel {} Voltage Monitor".format(channel["channel"])
                )
                channel["voltage_monitor"].set_lbls(
                    x_str="Time (pts)",
                    y_str="Voltage (V)"
                )

            # Set axis labels
            channel["trace"].set_lbls(
                x_str="Time (pts)",
                y_str="Frequency (THz)"
            )

    def run(self):
        """Runs the wavemeter monitor"""

        try:

            # Start the monitor with desired parameters
            # Raise is_running flag
            self._is_running = True

            # Set display to initial sample and show
            self._initialize_display()

            # Continuously update data until paused
            while self._is_running:

                # Keep track of time to refresh output
                start_time = time.time()
                while time.time() - start_time < self._update_rate and self._is_running:
                    self._update_data()
                    self._update_lock()
                    time.sleep(0.005)

                self._get_display_data()
                self._update_output()
                time.sleep(self._update_rate)

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """Stops the wavemeter monitor"""

        self._is_running = False

    def update_parameters(self, params):
        """
        Updates the monitoring script parameters during runtime. To be called remotely (see parameter_update module).

        :param params: List of dictionaries containing channel, setpoint, and lock parameters. Example:
            [{"channel": 1, "setpoint": 406.7, "lock": True}]
        """

        # Iterate through all channels to update
        for parameter in params:

            # Iterate through channels to find matching one
            channel_index = None
            for index, channel in enumerate(self.channels):
                if parameter["channel"] == channel["channel"]:
                    channel_index = index
                    break

            # If the channel is not currently running, raise an error
            if channel_index is None:
                msg_str = "Channel {} is not yet configured!".format(parameter["channel"])
                "Please restart wavemeter monitor with this channel"
                raise Exception(msg_str)

            # Otherwise just update the channel properties
            else:

                # Check that parameters are provided, and update them
                if "setpoint" in parameter:
                    self.channels[channel_index]["setpoint"] = parameter["setpoint"]
                if "lock" in parameter:
                    self.channels[channel_index]["lock"] = parameter["lock"]
                if "PID" in parameter:
                    self.channels["PID"].set_parameters(
                        p=parameter["PID"][0],
                        i=parameter["PID"][1],
                        d=parameter["PID"][2]
                    )
                if "memory" in parameter:
                    self.channels["PID"].set_parameters(memory=parameter["memory"])

    # Technical methods

    def _initialize_display(self):
        """Initializes the display, sets all output points to the first reading for each WL"""

        for channel in self.channels:

            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel["channel"])

            # Generate constant array with current wavelength for initialization
            channel["data"] = np.ones(self._data_length) * wavelength
            channel["display_data"] = np.ones(self._display_length) * wavelength

            # Set the data to the plot
            channel["trace"].set_data(
                x_ar=self._x_axis,
                y_ar=channel["display_data"]
                # y_ar=channel["data"]
            )

            # Plot the setpoint as well if it exists
            if channel["setpoint"] is not None:
                channel["sp_data"] = np.ones(self._data_length) * channel["setpoint"]
                channel["display_sp"] = np.ones(self._display_length) * channel["setpoint"]
                channel["trace"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_sp"]
                )

            # Show graph
            channel["trace"].show()

            # Plot error monitor if it exists
            if channel["error_monitor"] is not None:
                channel["error"] = np.ones(self._data_length) * channel["PID"].error
                channel["display_error"] = np.ones(self._display_length) * channel["PID"].error
                channel["error_monitor"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_error"]
                    # y_ar=channel["error"]
                )
                channel["error_monitor"].show()

            # Plot voltage monitor if it exists
            if channel["voltage_monitor"] is not None:
                channel["voltage"] = np.ones(self._data_length) * channel["PID"].cv
                channel["display_voltage"] = np.ones(self._display_length) * channel["PID"].cv
                channel["voltage_monitor"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_voltage"]
                    # y_ar=channel["voltage"]
                )
                channel["voltage_monitor"].show()

    def _update_data(self):
        """Pulls a new sample from the WLM into the data for each channel"""

        for channel in self.channels:
            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel["channel"])

            # Update output array
            channel["data"] = np.append(channel["data"][1:], wavelength)

            # Pull the most recent setpoint
            channel["sp_data"] = np.append(channel["sp_data"][1:], channel["setpoint"])

    def _update_setpoint(self):
        """Updates the setpoint to current value"""

        for channel in self.channels:

            # Update the setpoint if needed
            if channel["setpoint"] is not None:
                # Add the current setpoint to the data (in case it has changed)
                channel["sp_data"] = np.append(channel["sp_data"][1:], channel["setpoint"])

    def _update_output(self):
        """Updates the output with a new wavemeter sample"""

        for channel in self.channels:

            # Set data
            channel["trace"].set_data(
                x_ar=self._x_axis,
                y_ar=channel["display_data"]
                # y_ar=channel["data"]
            )

            # Plot the setpoint as well if provided
            if channel["setpoint"] is not None:
                # Set data
                channel["trace"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_sp"],
                    ind=1
                )

            # Plot monitors if desired
            if channel["error_monitor"] is not None:
                channel["error_monitor"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_error"]
                    # y_ar = channel["error"]
                )

            if channel["voltage_monitor"] is not None:
                channel["voltage_monitor"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["display_voltage"]
                    # y_ar=channel["voltage"]
                )

    def _get_display_data(self):
        """Generates data to be displayed from all wavemeter samples"""

        for channel in self.channels:

            # Bin the data
            current_data_index = 0
            current_display_index = 0
            monitor_setpoint = channel["setpoint"] is not None
            monitor_error = channel["error_monitor"] is not None
            monitor_voltage = channel["voltage_monitor"] is not None
            while current_data_index < self._data_length:
                channel["display_data"][current_display_index] = np.mean(
                    channel["data"][current_data_index:current_data_index+self._bin_by]
                )

                # Also compute display data for setpoint, error, and voltage if relevant
                if monitor_setpoint:
                    channel["display_sp"][current_display_index] = np.mean(
                        channel["sp_data"][current_data_index:current_data_index+self._bin_by]
                    )
                if monitor_error:
                    channel["display_error"][current_display_index] = np.mean(
                        channel["error"][current_data_index:current_data_index+self._bin_by]
                    )*1000
                if monitor_voltage:
                    channel["display_voltage"][current_display_index] = np.mean(
                        channel["voltage"][current_data_index:current_data_index+self._bin_by]
                    )
                current_data_index += self._bin_by
                current_display_index += 1

        # Update the setpoint
        # self._update_setpoint()

    def _update_lock(self):
        """Updates control variables for laser locking"""

        for channel in self.channels:

            # Check if the lock is on
            if channel["lock"]:

                # Feed in the data
                channel["PID"].set_pv(channel["data"][self._data_length - channel["PID"].memory:])

                # Make a step with the control variable
                channel["PID"].set_cv()

                # TODO: set voltage

                # Update error and lock attributes
                channel["error"] = np.append(channel["error"][1:], channel["PID"].error)
                channel["voltage"] = np.append(channel["voltage"][1:], channel["PID"].cv)

