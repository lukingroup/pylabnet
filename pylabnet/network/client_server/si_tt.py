import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_start_trace(self, name, ch_list=[1], bin_width=1000000000,
                            n_bins=10000):
        ch_list=pickle.loads(ch_list)
        return self._module.start_trace(
            name=name,
            ch_list=ch_list,
            bin_width=bin_width,
            n_bins=n_bins
        )

    def exposed_clear_ctr(self, name):
        return self._module.clear_ctr(name=name)

    def exposed_get_counts(self, name):
        res_pickle = self._module.get_counts(name=name)
        return pickle.dumps(res_pickle)

    def exposed_get_x_axis(self, name):
        res_pickle = self._module.get_x_axis(name=name)
        return pickle.dumps(res_pickle)

    def exposed_start_rate_monitor(self, name=None, ch_list=[1]):
        ch_list = pickle.loads(ch_list)
        return self._module.start_rate_monitor(name=name, ch_list=ch_list)

    def exposed_get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        res_pickle = self._module.get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.dumps(res_pickle)

    def exposed_start_gated_counter(self, name, click_ch, gate_ch, gated=True, bins=1000):
        return self._module.start_gated_counter(name, click_ch, gate_ch, gated, bins)

    def exposed_start_histogram(self, name, start_ch, click_ch, next_ch=-134217728,
                                sync_ch=-134217728, binwidth=1000, n_bins=1000,
                                n_histograms=1, start_delay=None):
        return self._module.start_histogram(name, start_ch, click_ch, next_ch=next_ch,
                                            sync_ch=sync_ch, binwidth=binwidth, n_bins=n_bins, n_histograms=n_histograms,
                                            start_delay=start_delay)

    def exposed_start_correlation(self, name, ch_1, ch_2, binwidth=1000, n_bins=1000, delay=None):
        return self._module.start_correlation(name, ch_1, ch_2, binwidth, n_bins, delay)

    def exposed_start(self, name):
        return self._module.start(name)

    def exposed_stop(self, name):
        return self._module.stop(name)

    def exposed_create_gated_channel(self, channel_name, click_ch, gate_ch, delay):
        return self._module.create_gated_channel(channel_name, click_ch, gate_ch, delay)

    def exposed_create_delayed_channel(self, channel_name, click_ch, delay):
        return self._module.create_delayed_channel(channel_name, click_ch, delay)

    def exposed_update_delay(self, channel_name, delay):
        return self._module.update_delay(channel_name, delay)

    def exposed_create_combined_channel(self, channel_name, channel_list):
        channel_list = pickle.loads(channel_list)
        return self._module.create_combined_channel(channel_name, channel_list)

    def exposed_set_trigger_level(self, channel, voltage):
        return self._module.set_trigger_level(channel, voltage)

class Client(ClientBase):

    def start_trace(self, name=None, ch_list=[1], bin_width=1000000000, n_bins=10000):
        """Start counter - used for count-trace applications

        :param name: (str) identifier for the counter measurement
        :param ch_list: (list) list of channels to count
        :param bin_width: integer in ps for width of count bins
        :param n_bins: integer number of bins to store before
                            wrapping around
        """

        ch_list = pickle.dumps(ch_list)
        return self._service.exposed_start_trace(
            name=name,
            ch_list=ch_list,
            bin_width=bin_width,
            n_bins=n_bins
        )

    def clear_ctr(self, name=None):
        """Resets the array to zero and restarts the measurement.
        Generic method for most measurement types.
        See the clear() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        return self._service.exposed_clear_ctr(name=name)

    def get_counts(self, name=None):
        """Gets a 2D array of counts on all channels. See the
            getData() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        res_pickle = self._service.exposed_get_counts(name=name)
        return pickle.loads(res_pickle)

    def get_x_axis(self, name=None):
        """Gets the x axis in picoseconds for the count array.
            See the getIndex() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        res_pickle = self._service.exposed_get_x_axis(name=name)
        return pickle.loads(res_pickle)

    def start_rate_monitor(self, name=None, ch_list=[1]):
        """Sets up a measurement for count rates

        :param name: (str) identifier for the counter
        :param ch_list: (list) list of channels to measure
        """

        ch_list = pickle.dumps(ch_list)
        return self._service.exposed_start_rate_monitor(name=name, ch_list=ch_list)

    def get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        """ Reports the current count rate

        :param name: (str) name of counter to use
        :param ctr_index: (int) index of counter to get data for
        :param integration: (float) roughly how long to measure for
        """

        res_pickle = self._service.exposed_get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.loads(res_pickle)

    def start_gated_counter(self, name, click_ch, gate_ch, bins=1000):
        """ Starts a new gated counter

        Starts counting at rising edge of gate, and returns count value into array
        after falling edge of gate

        :param name: (str) name of counter measurement to use
        :param click_ch: (int) click channel number -8...-1, 1...8
        :param gate_ch: (int) gate channel number -8...-1, 1...8
        :param bins: (int) number of bins (gate windows) to store
        """

        self._service.exposed_start_gated_counter(name, click_ch, gate_ch, True, bins)

    def count_between_markers(self, name, click_ch, marker_ch, bins=1000):
        """ Starts a new counter that counts at the rising edge of a marker
        
        Starts counting at rising edge of marker channel, and returns count value 
        into array at the next marker rising edge

        :param name: (str) name of counter measurement to use
        :param click_ch: (int) click channel number -8...-1, 1...8
        :param marker_ch: (int) marker channel number -8...-1, 1...8
        :param bins: (int) number of bins (gate windows) to store
        """

        self._service.exposed_start_gated_counter(name, click_ch, marker_ch, False, bins)

    def start_histogram(self, name, start_ch, click_ch, next_ch=-134217728,
                        sync_ch=-134217728, binwidth=1000, n_bins=1000,
                        n_histograms=1, start_delay=None):
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
        :param start_delay: (optional, int) delay for marker in ps
        """

        return self._service.exposed_start_histogram(name, start_ch, click_ch,
                                                     next_ch=next_ch,
                                                     sync_ch=sync_ch,
                                                     binwidth=binwidth, n_bins=n_bins,
                                                     n_histograms=n_histograms,
                                                     start_delay=start_delay)

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

        return self._service.exposed_start_correlation(
            name, ch_1, ch_2, binwidth, n_bins, delay
        )

    def start(self, name):
        """ Starts a measurement.

        Can be used to restart a measurement once it has been stopped
        :param name: (str) name of the measurement for identification
        """

        return self._service.exposed_start(name)

    def stop(self, name):
        """ Stops a measurement.

        Can be used to stop a measurement
        :param name: (str) name of the measurement for identification
        """

        return self._service.exposed_stop(name)

    def create_gated_channel(self, channel_name, click_ch, gate_ch, delay=None):
        """ Creates a virtual channel that is gated

        :param channel_name: (str) name of channel for future reference
        :param click_ch: (int) index of click channel -8...-1, 1...8
        :param gate_ch: (int) index of gate channel -8...-1, 1...8
            Assumes gate starts on rising edge (if positive) and ends
            on falling edge
        :param delay: (optional, float) amount to delay gate by
        """

        return self._service.exposed_create_gated_channel(
            channel_name, click_ch, gate_ch, delay
        )

    def create_delayed_channel(self, channel_name, click_ch, delay):
        return self._service.exposed_create_delayed_channel(channel_name, click_ch, delay)

    def create_combined_channel(self, channel_name, channel_list):
        """ Creates a combined virtual channel which includes events from multiple cahnnels 
        
        :param channel_name: (str) name, identifier of the channel
        :param channel_list: (list) list of channel numbers or names to combine
        """  
        return self._service.exposed_create_combined_channel(
            channel_name, pickle.dumps(channel_list)
        )

    def update_delay(self, channel_name, delay):
        """ Updates the delay for a gated + delayed channel

        :param channel_name: (str) identifier name of gated channel
        :param delay: (float) value of delay to update to in ps
        """

        return self._service.exposed_update_delay(channel_name, delay)

    def set_trigger_level(self, channel, voltage):
        return self._service.exposed_set_trigger_level(channel, voltage)
