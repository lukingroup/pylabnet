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

        self._is_running = False
        self._nd_trace = None
        self._ch_list = [1]
        self._num_ch = len(self._ch_list)
        self._ch_names = ['Channel 1']
        self._x_axis = np.arange(100)
        self._length = len(self._x_axis)
        self._y_axis = np.zeros((1,self._length))
        self._s_axis = None
        self._setpoints = [None]
        self._locks = [False]

    def set_params(self, ch_list=[1], setpoints=[None], locks=[False], display_pts=1000, units="Frequency (THz)"):
        """
        Configures script parameters for wavemeter control

        :param ch_list: array of wavemeter channels to log from 1-8
        :param setpoints: laser freqeuncy setpoints
        :param locks: whether or not to lock the laser
        :param display_pts: number of samples to display on plot
        :param units: string describing units of wavemeter output
        """

        self._ch_list = ch_list

        # Properly initialize setpoints if not provided
        if len(setpoints) == len(ch_list):
            self._setpoints = setpoints
        else:
            self._setpoints = []
            for channel in ch_list:
                self._setpoints.extend(None)

        self._locks = locks
        self._length = display_pts
        self._num_ch = len(self._ch_list)
        self._x_axis = np.arange(self._length)
        self._y_axis = np.zeros((self._num_ch, self._length))
        self._s_axis = np.zeros((self._num_ch, self._length))

        # Initialize GUI
        self._nd_trace = []
        for index, channel in enumerate(self._ch_list):

            # If a setpoint is given, prepare to plot it
            if self._setpoints[index] is not None:
                self._nd_trace.append(MultiTraceFig(
                    title_str="Channel {} Laser monitor".format(channel),
                    ch_names=["Channel {}".format(channel), "Channel {} SP".format(channel)],
                    shot_noise=False
                ))

            # Otherwise just a single plot for each channel
            else:
                self._nd_trace.append(MultiTraceFig(
                    title_str="Channel {} Laser monitor".format(channel),
                    ch_names=["Channel {}".format(channel)],
                    shot_noise=False
                ))

        for trace in self._nd_trace:
            trace.set_lbls(
                x_str="Time (pts)",
                y_str=units
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
                self._update_output()

                # Pause to give time for update
                time.sleep(0.05)

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """Pauses the wavemeter monitor"""

        self._is_running = False

    # Technical methods

    def _initialize_display(self):
        """Initializes the display, sets all output points to the first reading for each WL"""

        for index, channel in enumerate(self._ch_list):

            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel)

            # Generate constant array with current wavelength
            self._y_axis[index] = np.ones(self._length)*wavelength

            # Set data
            self._nd_trace[index].set_data(
                x_ar=self._x_axis,
                y_ar=self._y_axis[index]
            )

            # Plot the setpoint as well if provided
            if self._setpoints[index] is not None:
                self._s_axis[index] = np.ones(self._length)*self._setpoints[index]
                self._nd_trace[index].set_data(
                    x_ar=self._x_axis,
                    y_ar=self._s_axis[index],
                    ind=1
                )

            # Show graph
            self._nd_trace[index].show()

    def _update_output(self):
        """Updates the output with a new wavemeter sample"""

        for index, channel in enumerate(self._ch_list):
            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel)

            # Update output array
            self._y_axis[index] = np.append(self._y_axis[index][1:], wavelength)

            # Set data
            self._nd_trace[index].set_data(
                x_ar=self._x_axis,
                y_ar=self._y_axis[index]
            )

            # Plot the setpoint as well if provided
            if self._setpoints[index] is not None:

                # Add the current setpoint to the data (in case it has changed)
                # self._s_axis[index] = np.append(self._s_axis[index][1:], self._setpoints[index])

                # Set data
                self._nd_trace[index].set_data(
                    x_ar=self._x_axis,
                    y_ar=self._s_axis[index],
                    ind=1
                )


