""" Hardware wrapper for Swabian Instruments TimeTagger, including client and server access classes """

import TimeTagger as TT
import pickle
import time
import socket
import numpy as np
from pylabnet.utils.logging.logger import LogHandler


class Wrap:
    """ Wrapper for the full hardware interface to SITT.

    Can initialize multiple measurements with a single device/ same set of channels.
    Desired workflow:

    counter = Wrap(tagger, logger)
    counter.set_ch_assignment(name='count_trace', ch_list=[1,2,3])
    counter.start_ctr(name='count_trace')

    counter.set_ch_assignment(name='rate_monitor', ch_list=[1])
    counter.init_rate_monitor(name='rate_monitor')
    """

    def __init__(self, tagger, logger=None):
        """Instantiate count monitor

        :param tagger: instance of TimeTagger class
        :param ch_list: list of channels to count
        :param logger: instance of LogClient class, optional
        """

        # Log
        self.log = LogHandler(logger=logger)

        # Reference to tagger
        self._tagger = tagger

        # Log device ID information to demonstrate that connection indeed works
        serial = self._tagger.getSerial()
        model = self._tagger.getModel()
        self.log.info(
            'Got reference to Swabian Instruments TimeTagger device \n'
            'Serial number: {0}, Model: {1}'
            ''.format(serial, model)
        )

        # Counter instance
        self._ctr = {}

    def start_trace(self, name=None, ch_list=[1], bin_width=1000000000, 
                    n_bins=10000):
        """Start counter - used for count-trace applications

        :param name: (str) identifier for the counter measurement
        :param ch_list: (list) list of channels to count
        :param bin_width: integer in ps for width of count bins
        :param n_bins: integer number of bins to store before
                            wrapping around
        """

        # If a name is not provided just use the index of the measurement
        if name is None:
            name = str(len(self._ctr))

        # Instantiate Counter instance, see TT documentation
        self._ctr[name] = TT.Counter(
            self._tagger,
            channels=ch_list,
            binwidth=bin_width,
            n_values=n_bins
        )

        self.log.info('Set up count trace measurement on channel(s)'
                      f' {ch_list}')

    def clear_ctr(self, name=None):
        """Resets the array to zero and restarts the measurement.
        Generic method for most measurement types.
        See the clear() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Clear counter (see TT documentation)
        self._ctr[name].clear()

    def get_counts(self, name=None):
        """Gets a 2D array of counts on all channels. See the
            getData() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Get count data (see TT documentation)
        return self._ctr[name].getData()

    def get_x_axis(self, name=None):
        """Gets the x axis in picoseconds for the count array.
            See the getIndex() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Get x axis
        return self._ctr[name].getIndex()

    def start_rate_monitor(self, name=None, ch_list=[1]):
        """Sets up a measurement for count rates

        :param name: (str) identifier for the counter
        :param ch_list: (list) list of channels to measure
        """

        # If a name is not provided just use the index of the measurement
        if name is None:
            name = str(len(self._ctr))

        # Instantiate Counter instance, see TT documentation
        self._ctr[name] = TT.Countrate(
            self._tagger,
            channels=ch_list
        )

        self.log.info('Set up count rate measurement on channel(s)'
                      f' {ch_list}')

    def get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        """ Reports the current count rate

        :param name: (str) name of counter to use
        :param ctr_index: (int) index of counter to get data for
        :param integration: (float) roughly how long to measure for
        """

        self.clear_ctr(name=name)
        time.sleep(integration)
        return self._ctr[name].getData()

    def start_gated_counter(self, name, click_ch, gate_ch, bins=1000):
        """ Starts a new gated counter

        :param name: (str) name of counter measurement to use
        :param click_ch: (int) click channel number -8...-1, 1...8
        :param gate_ch: (int) gate channel number -8...-1, 1...8
        :param bins: (int) number of bins (gate windows) to store
        """

        self._ctr[name] = TT.CountBetweenMarkers(
            self._tagger,
            click_ch,
            gate_ch,
            end_channel=-gate_ch,
            n_values=bins
        )

    def start_histogram(self, name, start_ch, click_ch, next_ch=-134217728,
                        sync_ch=-134217728, binwidth=1000, n_bins=1000,
                        n_histograms=1):
        """ Sets up a Histogram measurement using the TT.TimeDifferences
        measurement class

        :param name: (str) name of measurement for future reference
        :param start_ch: (int) index of start channel -8...-1, 1...8
        :param click_ch: (int) index of counts channel -8...-1, 1...8
        :param next_ch: (int, optional) channel used to mark transition
            to next histogram (for multi-channel histograms)
        :param sync_ch: (int, optional) channel used to mark reset of
            histogram index
        :param binwidth: (int) width of bin in ps
        :param n_bins: (int) number of bins for total measurement
        :param n_histograms: (int) total number of histograms
        """

        self._ctr[name] = TT.TimeDifferences(
            tagger=self._tagger,
            click_channel=click_ch,
            start_channel=start_ch,
            next_channel=next_ch,
            sync_channel=sync_ch,
            binwidth=binwidth,
            n_bins=n_bins,
            n_histograms=n_histograms
        )
    
    
    @staticmethod
    def handle_name(name):
        if name is None:
            return '0'
        else:
            return name
