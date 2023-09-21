
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

    def exposed_get_ai_voltage(self, ao_channel, range):
        return self._module.get_ao_voltage(
            ao_channel=ao_channel,
            range=range
        )

    def exposed_ai_scan(self, low_ch, high_ch, num_samples, sample_rate, range):
        return self.module.ai_scan(
            low_ch=low_ch,
            high_ch=high_ch,
            num_samples=num_samples,
            sample_rate=sample_rate,
            range=range
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

    def get_ai_voltage(self, ao_channel, range):
        return self._service.exposed_get_ai_voltage(
            ao_channel=ao_channel,
            range=range
        )

    def ai_scan(self, low_ch, high_ch, num_samples, sample_rate, range):
        return self._service.exposed_ai_scan(
            low_ch=low_ch,
            high_ch=high_ch,
            num_samples=num_samples,
            sample_rate=sample_rate,
            range=range
        )

    def set_dio(self, digital_pin, value):
        return self._service.exposed_set_dio(
            digital_pin=digital_pin,
            value=value
        )
