import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_start_counting(self, name, bin_width=1000000000, n_bins=10000):
        return self._module.start_ctr(
            name=name,
            bin_width=bin_width,
            n_bins=n_bins
        )

    def exposed_clear_counter(self, name):
        return self._module.clear_ctr(name=name)

    def exposed_get_counts(self, name):
        res_pickle = self._module.get_counts(name=name)
        return pickle.dumps(res_pickle)

    def exposed_get_x_axis(self, name):
        res_pickle = self._module.get_x_axis(name=name)
        return pickle.dumps(res_pickle)

    def exposed_set_channels(self, name, ch_list=[1], gates=[]):
        return self._module.set_ch_assignment(
            name=name,
            ch_list=ch_list,
            gates=gates
        )

    def exposed_init_rate_monitor(self, name=None):
        return self._module.init_rate_monitor(name=name)

    def exposed_get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        res_pickle = self._module.get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.dumps(res_pickle)

    def exposed_setup_gated_counter(self, name, bins=1000):
        return self._module.setup_gated_counter(name, bins)


class Client(ClientBase):

    def start_counting(self, name=None, bin_width=1000000000, n_bins=10000):
        """Start counter - used for count-trace applications

        :param name: (str) identifier for the counter measurement
        :param bin_width: integer in ps for width of count bins
        :param n_bins: integer number of bins to store before
                            wrapping around
        """

        return self._service.exposed_start_counting(
            name=name,
            bin_width=bin_width,
            n_bins=n_bins
        )

    def clear_counter(self, name=None):
        """Resets the array to zero and restarts the measurement.
        Generic method for most measurement types.
        See the clear() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        return self._service.exposed_clear_counter(name=name)

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

    def set_channels(self, name=None, ch_list=[1], gates=[]):
        """Sets the ch_list attribute of the wrapper to a valid
            list of channel numbers as desired by TT, also
            configures the default naming convention for channels

        :param name: (str) identifier for the counter measurement
        :param ch_list: list of integer numbers of channels,
                        following the convention 1 ... 8
                        for rising edge and negative for falling
        :param gates: list of channels to use for gating
        """

        return self._service.exposed_set_channels(
            name=name,
            ch_list=ch_list,
            gates=gates
        )

    def init_rate_monitor(self, name=None):
        """Sets up a measurement for count rates

        :param name: (str) identifier for the counter
        :param ch_list: (list) list of channels to measure
        """

        return self._service.exposed_init_rate_monitor(name=name)

    def get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        """ Reports the current count rate

        :param name: (str) name of counter to use
        :param integration: (float) roughly how long to measure for
        """

        res_pickle = self._service.exposed_get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.loads(res_pickle)

    def setup_gated_counter(self, name, bins=1000):
        """ Starts a new gated counter

        :param name: (str) name of counter measurement to use
        :param bins: (int) number of bins (gate windows) to store
        """

        self._service.exposed_setup_gated_counter(name, bins)
