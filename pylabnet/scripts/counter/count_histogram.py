from pylabnet.network.client_server import si_tt
from pylabnet.utils.logging.logger import LogClient
from pylabnet.gui.igui.iplot import SingleTraceFig

import numpy as np
import time


class TimeTrace:
    """ Convenience class for handling time-trace measurements """

    def __init__(self, ctr: si_tt.Client, log: LogClient, 
                 click_ch=1, start_ch=2, binwidth=1000, n_bins=1000, update_interval=0.5, **kwargs):
        """ Instantiates TimeTrace measurement

        :param ctr: (si_tt.Client) client to timetagger hardware
        :param log: (LogClient) instance of logclient for logging
        :param **kwargs: additional keyword arguments including
            :param click_ch: (int) channel receiving clicks
            :param start_ch: (int) channel for starting histogram
            :param binwidth: (int) width of bins in ps
            :param n_bins: (int) total number of bins for histogram
            :param update_interval: (float) interval in seconds to wait between updates
                Note, don't go too small (< 100 ms, not precisely tested yet), 
                otherwise we might lag in jupyter notebook
            TODO: in future, can implement multiple histograms if useful
        """

        self.ctr = ctr
        self.log = log

        # Store histogram parameters
        self.click_ch = click_ch
        self.start_ch = start_ch
        self.binwidth = binwidth
        self.n_bins = n_bins

        self.hist = f'histogram_{np.random.randint(1000)}'
        self.plot = None
        self.is_paused = False
        self.up_in = update_interval

    def start_acquisition(self):
        """ Begins time-trace acquisition """

        self.ctr.start_histogram(
            name=self.hist,
            start_ch=self.start_ch,
            click_ch=self.click_ch,
            binwidth=self.binwidth,
            n_bins=self.n_bins
        )

    def init_plot(self):
        """ Instantiates a plot, assuming counter is live """

        self.plot = SingleTraceFig(title_str='Count Histogram')
        self.plot.set_data(
            x_ar=self.ctr.get_x_axis(self.hist),
            y_ar=self.ctr.get_counts(self.hist)    
        )
        self.plot.show()

    def _update_data(self):
        """ Updates to the current data """

        self.plot.set_data(
            x_ar=self.ctr.get_x_axis(self.hist),
            y_ar=self.ctr.get_counts(self.hist)    
        )
    
    def go(self):
        """ Runs counter from scratch """
        
        self.start_acquisition()
        self.init_plot()

        self.is_paused = False
        while not self.is_paused:

            time.sleep(self.up_in)
            self._update_data

    def resume(self):
        """ Runs an already instantiated counter."""

        self.is_paused = False
        while not self.is_paused:

            time.sleep(self.up_in)
            self._update_data

    def clear(self):
        """ Clears the data """

        self.ctr.clear_ctr(name=self.hist)

    def pause(self):
        """ Pauses the go/run loop. 

        NOTE: does not actually stop counter acquisition! 
        There does not seem to be a way to do that from SI-TT API
        """

        self.is_paused = True
