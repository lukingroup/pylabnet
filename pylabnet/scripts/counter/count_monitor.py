""" Generic script for monitoring counts from a counter """

import numpy as np
from pylabnet.gui.pyqt.gui_handler import GUIHandler


# Static methods

def generate_widgets():
    """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""

    graphs, legends, numbers = [], [], []
    for i in range(2):
        graphs.append('graph_widget_' + str(i + 1))
        legends.append('legend_widget_' + str(i + 1))
        numbers.append('number_label_' + str(i + 1))
    for i in range(2, 8):
        numbers.append('number_label_' + str(i + 1))
    return graphs, legends, numbers


class CountMonitor:

    # Generate all widget instances for the .ui to use
    _plot_widgets, _legend_widgets, _number_widgets = generate_widgets()

    def __init__(self, ctr_client, gui_client, logger_client):
        """ Constructor for CountMonitor script

        :param ctr_client: (optional) instance of hardware client for counter
        :param gui_client: (optional) instance of client of desired output GUI
        :param logger_client: (obj) instance of logger client.
        """

        self._ctr = ctr_client
        self._bin_width = None
        self._n_bins = None
        self._ch_list = None
        self._plot_list = None  # List of channels to assign to each plot (e.g. [[1,2], [3,4]])
        self._plots_assigned = []  # List of plots on the GUI that have been assigned


        # Instanciate gui handler
        self.gui_handler = GUIHandler(gui_client, logger_client)

    def set_hardware(self, ctr):
        """ Sets hardware client for this script

        :param ctr: instance of count monitor hardware client
        """

        # Initialize counter instance
        self._ctr = ctr

    def set_params(self, bin_width=1e9, n_bins=1e4, ch_list=[1], plot_list=None):
        """ Sets counter parameters
        
        :param bin_width: bin width in ps
        :param n_bins: number of bins to display on graph
        :param ch_list: (list) channels to record
        :param plot_list: list of channels to assign to each plot (e.g. [[1,2], [3,4]])
        """

        # Save params to internal variables
        self._bin_width = int(bin_width)
        self._n_bins = int(n_bins)
        self._ch_list = ch_list
        self._plot_list = plot_list

        # Configure counting channels
        self._ctr.set_channels(ch_list=ch_list)

    def run(self):
        """ Runs the counter from scratch"""

        try:

            # Start the counter with desired parameters
            self._initialize_display()
            self._is_running = True
            self._ctr.start_counting(bin_width=self._bin_width, n_bins=self._n_bins)

            # Continuously update data until paused
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """ Pauses the counter"""

        self._is_running = False

    def resume(self):
        """ Resumes the counter.
        
        To be used to resume after the counter has been paused.
        """

        try:
            self._is_running = True

            # Clear counter and resume plotting
            self._ctr.clear_counter()
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    # Technical methods

    def _initialize_display(self):
        """ Initializes the display (configures all plots) """

        plot_index = 0
        for channel in self._ch_list:

            # Figure out which plot to assign to
            if self._plot_list is not None:
                for index, channel_set in enumerate(self._plot_list):
                    if channel in channel_set:
                        plot_index = index
                        break

            # If we have not assigned this plot yet, assign it
            if plot_index not in self._plots_assigned:
                self.gui_handler.assign_plot(
                    plot_widget=self._plot_widgets[plot_index],
                    plot_label='Counter Monitor {}'.format(plot_index + 1),
                    legend_widget=self._legend_widgets[plot_index]
                )
                self._plots_assigned.append(plot_index)

            # Now assign this curve
            self.gui_handler.assign_curve(
                plot_label='Counter Monitor {}'.format(plot_index + 1),
                curve_label='Channel {}'.format(channel),
                error=True
            )

            # Assign scalar
            self.gui_handler.assign_label(
                label_widget=self._number_widgets[channel - 1],
                label_label='Channel {}'.format(channel)
            )


    def _update_output(self):
        """ Updates the output to all current values"""

        # Update all active channels
        # x_axis = self._ctr.get_x_axis()/1e12
        counts = self._ctr.get_counts()
        counts_per_sec = counts*(1e12/self._bin_width)
        noise = np.sqrt(counts)*(1e12/self._bin_width)
        plot_index = 0

        for index, count_array in enumerate(counts_per_sec):

            # Figure out which plot to assign to
            channel = self._ch_list[index]
            if self._plot_list is not None:
                for index_plot, channel_set in enumerate(self._plot_list):
                    if channel in channel_set:
                        plot_index = index_plot
                        break

            # Update GUI data

            self.gui_handler.set_curve_data(
                data=count_array,
                error=noise[index],
                plot_label='Counter Monitor {}'.format(plot_index + 1),
                curve_label='Channel {}'.format(channel)
            )
            self.gui_handler.set_label(
                text='{:.4e}'.format(count_array[-1]),
                label_label='Channel {}'.format(channel)
            )
