from pylabnet.gui.igui.iplot import MultiTraceFig
import numpy as np


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
        self._ch_names = ['Channel 1']
        self._x_axis = np.arange(100)
        self._length = len(self._x_axis)
        self._y_axis = np.zeros((1,self._length))

    def set_params(self, ch_list=[1], display_pts=100, title_str='Wavemeter monitor', units="Frequency (THz)"):
        """
        Configures script parameters for wavemeter control

        :param ch_list: array of wavemeter channels to log from 1-8
        :param display_pts: number of samples to display on plot
        :param title_str: title of plot
        :param units: string describing units of wavemeter output
        """

        self._ch_list = ch_list
        self._length = display_pts
        self._x_axis = np.arange(self._length)
        self._y_axis = np.zeros((1,self._length))

        # Create array for channel names
        name_list = []
        for channel in self._ch_list:
            name_list.extend(str(channel))
        self._ch_names = name_list

        # Initialize GUI
        self._nd_trace = MultiTraceFig(
            title_str=title_str,
            ch_names=self._ch_names,
            shot_noise=False
        )
        self._nd_trace.set_lbls(
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
            self._nd_trace.set_data(
                x_ar=self._x_axis,
                y_ar=self._y_axis[index]
            )

        # Show graph
        self._nd_trace.show()

    def _update_output(self):
        """Updates the output with a new wavemeter sample"""

        for index, channel in enumerate(self._ch_list):
            # Get current wavelength
            wavelength = self._wlm.get_wavelength(channel)

            # Update output array
            self._y_axis[index] = np.append(self._y_axis[index][1:], wavelength)

            # Set data
            self._nd_trace.set_data(
                x_ar=self._x_axis,
                y_ar=self._y_axis[index]
            )




