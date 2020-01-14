from pylabnet.scripts.pid import PID
import numpy as np
import time


# Static methods

def generate_widgets():
    """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""
    graphs, legends, numbers, booleans = [], [], [], []

    for i in range(4):
        graphs.append('graph_widget_'+str(i+1))
        legends.append('legend_widget_'+str(i+1))
        numbers.append('number_widget_'+str(i+1))
        booleans.append('boolean_widget_'+str(i+1))
    for i in range(4, 8):
        numbers.append('number_widget_' + str(i + 1))
        booleans.append('boolean_widget_' + str(i + 1))
    return graphs, legends, numbers, booleans


# Main class

# noinspection PyTypeChecker
class WlmMonitor:
    """Script class for monitoring wavemeter"""

    # Name of GUI template to use
    _ui = "wavemetermonitor_4ch"

    # Define GUI widget instance names for assignment of data
    _gui_plot_widgets, _gui_legend_widgets, _gui_number_widgets, _gui_boolean_widgets = generate_widgets()

    def __init__(self, wlm_client=None):

        # Store wavemeter client
        if wlm_client is None:
            msg_str = "Please pass wavemeter client in order to instantiate WlmMonitor script."
            raise Exception(msg_str)

        self._wlm = wlm_client
        self._is_running = False
        self.channels = [None]
        self._display_pts = 0
        self._gui = None

    def set_params(self, channels=None, gui=None, display_pts=1000, memory=10):
        """
        Configures script parameters for wavemeter control
        
        :param channels: list of dictionaries containing channel information in the example structure:
            {"channel": 1, "setpoint": None, "lock": False, "PID":[0, 0, 0]}
        :param gui: instance of GUI client for data streaming
            Note: this should be increased in order to avoid lagging in plot outputting
        :param display_pts: number of points to display on graph
        :param memory: number of points to use for integral memory
        """

        self._display_pts = display_pts
        self._gui = gui

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
            if channel["setpoint"] is not None:

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
                # channel["error_monitor"] = SingleTraceFig(
                #     title_str="Channel {} Lock Error Monitor".format(channel["channel"])
                # )
                # channel["error_monitor"].set_lbls(
                #     x_str="Time (pts)",
                #     y_str="Lock error (GHz)"
                # )
                # channel["voltage_monitor"] = SingleTraceFig(
                #     title_str="Channel {} Voltage Monitor".format(channel["channel"])
                # )
                # channel["voltage_monitor"].set_lbls(
                #     x_str="Time (pts)",
                #     y_str="Voltage (V)"
                # )

    def run(self):
        """Runs the wavemeter monitor"""

        try:
            self._is_running = True

            # Set display to initial sample and show
            self._initialize_display()

            # Continuously update data and lock until paused
            while self._is_running:
                self._update_data()
                self._update_lock()

                # Sleep slightly longer than the max query time
                time.sleep(0.003)

                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """Stops the wavemeter monitor"""

        self._is_running = False

    def resume(self):
        """Resumes wavemeter monitor after it has been paused"""

        try:
            self._is_running = True

            # Continuously update data and lock until paused
            while self._is_running:
                self._update_data()
                self._update_lock()

                # Sleep slightly longer than the max query time
                time.sleep(0.003)

                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

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
        """Initializes the display, sets all data to the first reading for each WL"""

        # Keep track of how many graphs we initialize so we don't overload the GUI
        graph_index = 0
        num_graphs = len(self._gui_plot_widgets)
        while graph_index < num_graphs and graph_index < len(self.channels):

            # Assign main channel GUI labels
            current_channel = self.channels[graph_index]["channel"]
            self.channels[graph_index]["plot_label"] = "Channel {} Wavemeter Monitor".format(current_channel)
            self.channels[graph_index]["curve_label"] = "Laser {} Frequency".format(current_channel)

            # Configure plot
            self._gui.assign_plot(
                plot_widget=self._gui_plot_widgets[graph_index],
                plot_label=self.channels[graph_index]['plot_label']
            )

            # Configure frequency monitoring curve
            self._gui.assign_curve(
                plot_label=self.channels[graph_index]['plot_label'],
                curve_label=self.channels[graph_index]['curve_label']
            )

            # Configure frequency display, keeping in mind there are 2 number widgets per channel
            self._gui.assign_scalar(
                scalar_widget=self._gui_number_widgets[2*graph_index],
                scalar_label=self.channels[graph_index]['curve_label']
            )

            # Set data array
            self.channels[graph_index]["data"] = np.ones(self._display_pts)*self._wlm.get_wavelength()

            # Assign setpoint to the sames plot (but a new curve) if relevant
            if self.channels[graph_index]["setpoint"] is not None:
                self.channels[graph_index]["sp_label"] = "Channel {} Setpoint".format(current_channel)
                self._gui.assign_curve(
                    plot_label=self.channels[graph_index]['plot_label'],
                    curve_label=self.channels[graph_index]['sp_label']
                )

                # Configure setpoint display
                self._gui.assign_scalar(
                    scalar_widget=self._gui_number_widgets[2*graph_index+1],
                    scalar_label=self.channels[graph_index]['sp_label']
                )

                # Set setpoint array
                self.channels[graph_index]["sp_data"] = (np.ones(self._display_pts)
                                                         * self.channels[graph_index]["setpoint"])

                # Set lock booleans
                self.channels[graph_index]['lock_label'] = 'Channel {} Lock'.format(current_channel)
                self.channels[graph_index]['error_label'] = 'Channel {} Error'.format(current_channel)
                self._gui.assign_scalar(
                    scalar_widget=self._gui_boolean_widgets[2*graph_index],
                    scalar_label=self.channels[graph_index]['lock_label']
                )
                self._gui.assign_scalar(
                    scalar_widget=self._gui_boolean_widgets[2*graph_index+1],
                    scalar_label=self.channels[graph_index]['error_label']
                )

            # Proceed to the next channel
            graph_index += 1

    def _update_data(self):
        """Pulls a new sample from the WLM into the data for each channel"""

        for channel in self.channels:

            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel["channel"])

            # Update output array
            channel["data"] = np.append(channel["data"][1:], wavelength)

            # Pull the most recent setpoint
            if channel["setpoint"] is not None:
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

            # Update main trace
            self._gui.set_curve_data(
                channel["data"],
                plot_label=channel["plot_label"],
                curve_label=channel["curve_label"]
            )

            # Update current WL
            self._gui.set_scalar(
                value=channel['data'][-1],
                scalar_label=channel['curve_label']
            )

            # Update setpoint if relevant
            if channel["setpoint"] is not None:
                self._gui.set_curve_data(
                    channel["sp_data"],
                    plot_label=channel["plot_label"],
                    curve_label=channel["sp_label"]
                )
                self._gui.set_scalar(
                    value=channel['sp_data'][-1],
                    scalar_label=channel['sp_label']
                )

            # Plot monitors if desired
            # if channel["error_monitor"] is not None:
            #     channel["error_monitor"].set_data(
            #         x_ar=self._x_axis,
            #         y_ar=channel["display_error"]
            #         # y_ar = channel["error"]
            #     )
            #
            # if channel["voltage_monitor"] is not None:
            #     channel["voltage_monitor"].set_data(
            #         x_ar=self._x_axis,
            #         y_ar=channel["display_voltage"]
            #         # y_ar=channel["voltage"]
            #     )

    def _get_display_data(self):
        """Generates data to be displayed from all wavemeter samples"""

        for channel in self.channels:

            # Bin the data
            current_data_index = 0
            current_display_index = 0
            monitor_setpoint = channel["setpoint"] is not None
            monitor_error = "error_monitor" in channel
            monitor_voltage = "voltage_monitor" in channel
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

    def _update_lock(self):
        """Updates control variables for laser locking"""

        for channel in self.channels:

            # Check if the lock is on
            if channel["lock"]:

                # Feed in the data
                channel["PID"].set_pv(channel["data"][self._display_pts - channel["PID"].memory:])

                # Make a step with the control variable
                channel["PID"].set_cv()

                # TODO: set voltage

                # Update error and lock attributes
                # channel["error"] = np.append(channel["error"][1:], channel["PID"].error)
                # channel["voltage"] = np.append(channel["voltage"][1:], channel["PID"].cv)
