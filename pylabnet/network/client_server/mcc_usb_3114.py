
import pickle
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_ao_voltage(self, ao_channel, voltage_pickle):
        voltage = pickle.loads(voltage_pickle)
        return self._module.set_ao_voltage(
            ao_channel=ao_channel,
            voltage=voltage
        )

    def exposed_set_dio(self, digital_pin, value):
        return self._module.set_dio(
            digital_pin=digital_pin,
            value=value
        )


class Client(ClientBase):

    def set_ao_voltage(self, ao_channel, voltage):
        voltage_pickle = pickle.dumps(voltage)
        return self._service.exposed_set_ao_voltage(
            ao_channel=ao_channel,
            voltage_pickle=voltage_pickle
        )

    def set_dio(self, digital_pin, value):
        return self._service.exposed_set_dio(
            digital_pin=digital_pin,
            value=value
        )
