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
        self._channels = {}

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

        ch_list = [self._get_channel(ch) for ch in ch_list]

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

    def start_gated_counter(self, name, click_ch, gate_ch, gated=True, bins=1000):
        """ Starts a new gated counter

        :param name: (str) name of counter measurement to use
        :param click_ch: (int) click channel number -8...-1, 1...8
        :param gate_ch: (int) gate channel number -8...-1, 1...8
        :param gated: (bool) whether or not to physicall gate, or just count between
            gate_ch edges
        :param bins: (int) number of bins (gate windows) to store
        """

        if gated:
            self._ctr[name] = TT.CountBetweenMarkers(
                self._tagger,
                self._get_channel(click_ch),
                self._get_channel(gate_ch),
                end_channel=-gate_ch,
                n_values=bins
            )
        else:
            self._ctr[name] = TT.CountBetweenMarkers(
                self._tagger,
                self._get_channel(click_ch),
                self._get_channel(gate_ch),
                n_values=bins
            )

    def start_histogram(self, name, start_ch, click_ch, next_ch=-134217728,
                        sync_ch=-134217728, binwidth=1000, n_bins=1000,
                        n_histograms=1, start_delay=None):
        """ Sets up a Histogram measurement using the TT.TimeDifferences
        measurement class

        :param name: (str) name of measurement for future reference
        :param start_ch: (int) index of start channel -8...-1, 1...8
        :param click_ch: (int or str) index of counts channel -8...-1, 1...8
            if physical, otherwise channel name if virtual
        :param next_ch: (int, optional) channel used to mark transition
            to next histogram (for multi-channel histograms)
        :param sync_ch: (int, optional) channel used to mark reset of
            histogram index
        :param binwidth: (int) width of bin in ps
        :param n_bins: (int) number of bins for total measurement
        :param n_histograms: (int) total number of histograms
        :param start_delay: (optional, int) delay for marker in ps
        """

        if start_delay is not None:
            self._channels[name] = TT.DelayedChannel(
                tagger=self._tagger,
                input_channel=start_ch,
                delay=start_delay
            )
            start_ch = name

        self._ctr[name] = TT.TimeDifferences(
            tagger=self._tagger,
            click_channel=self._get_channel(click_ch),
            start_channel=self._get_channel(start_ch),
            next_channel=next_ch,
            sync_channel=sync_ch,
            binwidth=binwidth,
            n_bins=n_bins,
            n_histograms=n_histograms
        )

    def start_correlation(self, name, ch_1, ch_2, binwidth=1000, n_bins=1000, delay=None):
        """ Sets up a correlation measurement using TT.Correlation measurement class

        :param name: (str) name of measurement for future reference
        :param ch_1: (int or str) index of first click channel -8...-1, 1...8
            if physical, otherwise channel name if virtual
        :param ch_2: (int or str) index of second click channel -8...-1, 1...8
            if physical, otherwise channel name if virtual
        :param binwidth: (int) width of bin in ps
        :param n_Bins: (int) number of bins for total measurement
        :param delay: (optional, int) delay for channel 1
        """

        if delay is not None:
            label = f'{name}_delayed'
            self._channels[label] = TT.DelayedChannel(
                tagger=self._tagger,
                input_channel=self._get_channel(ch_1),
                delay=int(delay)
            )
            ch_1 = label

        self._ctr[name] = TT.Correlation(
            tagger=self._tagger,
            channel_1=self._get_channel(ch_1),
            channel_2=self._get_channel(ch_2),
            binwidth=binwidth,
            n_bins=n_bins
        )

    def start(self, name):
        """ Starts a measurement.

        Can be used to restart a measurement once it has been stopped
        :param name: (str) name of the measurement for identification
        """

        self._ctr[name].start()

    def stop(self, name):
        """ Stops a measurement.

        Can be used to stop a measurement
        :param name: (str) name of the measurement for identification
        """

        self._ctr[name].stop()

    def create_gated_channel(self, channel_name, click_ch, gate_ch, delay=None):
        """ Creates a virtual channel that is gated

        :param channel_name: (str) name of channel for future reference
        :param click_ch: (int) index of click channel -8...-1, 1...8
        :param gate_ch: (int) index of gate channel -8...-1, 1...8
            Assumes gate starts on rising edge (if positive) and ends
            on falling edge
        :param delay: (optional, float) amount to delay gate by
        """

        # Create a delayed channel for the gate if needed
        if delay is not None:
            self._channels[f'{channel_name}_delayed'] = TT.DelayedChannel(
                tagger=self._tagger,
                input_channel= gate_ch,
                delay=int(delay)
            )
            self._channels[f'{channel_name}_delayed_falling'] = TT.DelayedChannel(
                tagger=self._tagger,
                input_channel=-gate_ch,
                delay=int(delay)
            )
            self.log.info(f'Created delayed gate {channel_name}_delayed for gate channel {gate_ch}')
            gate_ch = self._get_channel(f'{channel_name}_delayed')
            gate_stop_ch = self._get_channel(f'{channel_name}_delayed_falling')
        else:
            gate_stop_ch = -gate_ch

        self._channels[channel_name] = TT.GatedChannel(
            tagger=self._tagger,
            input_channel=self._get_channel(click_ch),
            gate_start_channel=self._get_channel(gate_ch),
            gate_stop_channel=self._get_channel(gate_stop_ch)
        )
        self.log.info(f'Created gated channel {channel_name}, '
                      f'click channel: {click_ch}, gate channel: {gate_ch}')

    def create_delayed_channel(self, channel_name, click_ch, delay):
        """ Creates a delayed virtual channel allowing for a user to input a delay
        :param channel_name: (str) name, identifier of the channel
        :param click_ch: (int) index of  channel
        :param delay: (optional, int) amount to delay by
        """
        self._channels[channel_name] = TT.DelayedChannel(
            tagger=self._tagger,
            input_channel=self._get_channel(click_ch),
            delay=int(delay)
        )
        self.log.info(f'Created delayed channel {channel_name}, '
                      f'click channel: {click_ch}, delay: {delay}')


    def create_combined_channel(self, channel_name, channel_list):
        """ Creates a combined virtual channel which includes events from multiple cahnnels

        :param channel_name: (str) name, identifier of the channel
        :param channel_list: (list) list of channel numbers or names to combine
        """

        # Handle virtual channels in channel_list
        channels = [self._get_channel(ch) for ch in channel_list]
        self._channels[channel_name] = TT.Combiner(
            tagger=self._tagger,
            channels=channels
        )

    def update_delay(self, channel_name, delay):
        """ Updates the delay for a gated + delayed channel

        :param channel_name: (str) identifier name of gated channel
        :param delay: (float) value of delay to update to in ps
        """

        self._channels[f'{channel_name}_delayed'].setDelay(int(delay))
        self._channels[f'{channel_name}_delayed_falling'].setDelay(int(delay))
        self.log.info(f'Updated {channel_name} delay to {delay}')

    def _get_channel(self, ch):
        """ Handle virtual channel input

        :param ch: (int or str) channel index (if physical) or name (virtual)

        :return: (int) channel number of physical or virtual channel
        """

        if isinstance(ch, str):
            return self._channels[ch].getChannel()
        else:
            return ch

    @staticmethod
    def handle_name(name):
        if name is None:
            return '0'
        else:
            return name
