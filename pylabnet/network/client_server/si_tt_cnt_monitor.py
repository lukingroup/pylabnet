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

    def exposed_set_channels(self, name, ch_list=[1]):
        return self._module.set_ch_assignment(
            name=name,
            ch_list=ch_list
        )

    def exposed_get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        res_pickle = self._module.get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.dumps(res_pickle)


class Client(ClientBase):

    def start_counting(self, name=None, bin_width=1000000000, n_bins=10000):
        return self._service.exposed_start_counting(
            name=name,
            bin_width=bin_width,
            n_bins=n_bins
        )

    def clear_counter(self, name=None):
        return self._service.exposed_clear_counter(name=name)

    def get_counts(self, name=None):
        res_pickle = self._service.exposed_get_counts(name=name)
        return pickle.loads(res_pickle)

    def get_x_axis(self, name=None):
        res_pickle = self._service.exposed_get_x_axis(name=name)
        return pickle.loads(res_pickle)

    def set_channels(self, name=None, ch_list=[1]):
        return self._service.exposed_set_channels(
            name=name,
            ch_list=ch_list
        )

    def get_count_rate(self, name=None, ctr_index=0, integration=0.1):
        res_pickle = self._service.exposed_get_count_rate(
            name=name,
            ctr_index=ctr_index,
            integration=integration
        )
        return pickle.loads(res_pickle)

