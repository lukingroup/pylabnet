import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.network.core.generic_server import GenericServer


class Service(ServiceBase):

    def exposed_start_counting(self, bin_width=1000000000, n_bins=10000):
        return self._module.start_ctr(
            bin_width=bin_width,
            n_bins=n_bins
        )

    def exposed_clear_counter(self):
        return self._module.clear_ctr()

    def exposed_get_counts(self):
        res_pickle = self._module.get_counts()
        return pickle.dumps(res_pickle)

    def exposed_get_x_axis(self):
        res_pickle = self._module.get_x_axis()
        return pickle.dumps(res_pickle)

    def exposed_set_channels(self, ch_list=[1]):
        return self._module.set_ch_assignment(
            ch_list=ch_list
        )


class Client(ClientBase):

    def start_counting(self, bin_width=1000000000, n_bins=10000):
        return self._service.exposed_start_counting(
            bin_width=bin_width,
            n_bins=n_bins
        )

    def clear_counter(self):
        return self._service.exposed_clear_counter()

    def get_counts(self):
        res_pickle = self._service.exposed_get_counts()
        return pickle.loads(res_pickle)

    def get_x_axis(self):
        res_pickle = self._service.exposed_get_x_axis()
        return pickle.loads(res_pickle)

    def set_channels(self, ch_list=[1]):
        return self._service.exposed_set_channels(
            ch_list=ch_list
        )

