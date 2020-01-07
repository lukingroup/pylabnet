from pylabnet.gui.igui.iplot import MultiTraceFig
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

        # self._is_running = False
        # self._nd_trace = None
        # self._ch_list = [1]
        # self._num_ch = len(self._ch_list)
        # self._ch_names = ['Channel 1']
        # self._x_axis = np.arange(100)
        # self._length = len(self._x_axis)
        # self._y_axis = np.zeros((1,self._length))
        # self._s_axis = None
        # self._setpoints = [None]
        # self._locks = [False]

        self._is_running = False
        self.channels = [None]
        self._x_axis = None
        self._data_length = 0
        self._display_length = 0
        self._update_rate = 0
        self._bin_by = 0

    def set_params(self, channels=None, update_rate=0.05, display_pts=1000, bin_by=5):
        """
        Configures script parameters for wavemeter control
        
        :param channels: list of dictionaries containing channel information in the example structure:
            {"channel": 1, "setpoint": None, "lock": False}
        :param update_rate: how often to update the plot in seconds
            Note: this should be increased in order to avoid lagging in plot outputting
        :param display_pts: number of points to display on graph
        :param bin_by: number of wavemeter samples per display point
        """

        self._bin_by = bin_by
        self._display_length = display_pts
        self._data_length =self._display_length * self._bin_by
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
            # Add placeholder for data & display data
            channel["data"] = np.zeros(self._data_length)
            channel["display_data"] = np.zeros(self._display_length)

            # We need to configure the plot differently based on whether or not a setpoint is given
            if channel["setpoint"] is None:
                channel["sp_data"] = None

                # Initialize plot with no setpoints
                channel["trace"] = MultiTraceFig(title_str="Channel {} Laser Monitor".format(channel["channel"]))

            else:
                channel["sp_data"] = np.ones(self._display_length) * channel["setpoint"]

                # Initialize plot with setpoints
                channel["trace"] = MultiTraceFig(
                    title_str="Channel {} Laser Monitor".format(channel["channel"]),
                    ch_names=["Channel {} Frequency".format(channel["channel"]),
                              "Channel {} Setpoint".format(channel["channel"])]
                )

            # Set labels
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

                # Keep track of time to refresh output only when desired
                start_time = time.time()
                while time.time() - start_time < self._update_rate and self._is_running:
                    self._update_data()

                    # Wait approximately the query time
                    time.sleep(0.002)
                if self._is_running:
                    self._get_display_data()
                    self._update_output()

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
                self.channels[channel_index]["setpoint"], self.channels[channel_index]["lock"] = (parameter["setpoint"],
                                                                                                  parameter["lock"])
                foo = 0
            return foo

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
            )

            # Plot the setpoint as well if it exists
            if channel["setpoint"] is not None:
                channel["sp_data"] = np.ones(self._display_length) * channel["setpoint"]
                channel["trace"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["sp_data"]
                )

            # Show graph
            channel["trace"].show()

    def _update_data(self):
        """Pulls a new sample from the WLM into the data for each channel"""

        for channel in self.channels:
            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel["channel"])

            # Update output array
            channel["data"] = np.append(channel["data"][1:], wavelength)

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
            )

            # Plot the setpoint as well if provided
            if channel["setpoint"] is not None:
                # Set data
                channel["trace"].set_data(
                    x_ar=self._x_axis,
                    y_ar=channel["sp_data"],
                    ind=1
                )

    def _get_display_data(self):
        """Generates data to be displayed from all wavemeter samples"""

        for channel in self.channels:

            # Bin the data
            current_data_index = 0
            current_display_index = 0
            while current_data_index < self._data_length:
                channel["display_data"][current_display_index] = np.mean(
                    channel["data"][current_data_index:current_data_index+self._bin_by]
                )
                current_data_index += self._bin_by
                current_display_index += 1

        # Update the setpoint
        self._update_setpoint()

