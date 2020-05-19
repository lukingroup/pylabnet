import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_ao_voltage(self, ao_channel, voltage_pickle):
        voltages = pickle.loads(voltage_pickle)
        return self._module.set_ao_voltage(
            ao_channel=ao_channel,
            voltages=voltages
        )


class Client(ClientBase):

    def set_ao_voltage(self, ao_channel, voltages):
        voltage_pickle = pickle.dumps(voltages)
        return self._service.exposed_set_ao_voltage(
            ao_channel=ao_channel,
            voltage_pickle=voltage_pickle
        )