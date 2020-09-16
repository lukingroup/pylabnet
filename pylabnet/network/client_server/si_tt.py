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

    def exposed_start_gated_counter(self, name, click_ch, gate_ch, bins=1000):
        return self._module.start_gated_counter(name, click_ch, gate_ch, bins)

    def exposed_start_histogram(self, name, start_ch, click_ch, next_ch=-134217728,
                                sync_ch=-134217728, binwidth=1000, n_bins=1000,
                                n_histograms=1):
        return self._module.start_histogram(name, start_ch, click_ch, next_ch=next_ch,
                                            sync_ch=sync_ch, binwidth=binwidth, n_bins=n_bins, n_histograms=n_histograms)


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

        :param name: (str) name of counter measurement to use
        :param click_ch: (int) click channel number -8...-1, 1...8
        :param gate_ch: (int) gate channel number -8...-1, 1...8
        :param bins: (int) number of bins (gate windows) to store
        """

        self._service.exposed_start_gated_counter(name, click_ch, gate_ch, bins)

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

        return self._service.exposed_start_histogram(name, start_ch, click_ch,
                                                     next_ch=next_ch,
                                                     sync_ch=sync_ch,
                                                     binwidth=binwidth, n_bins=n_bins,
                                                     n_histograms=n_histograms)
