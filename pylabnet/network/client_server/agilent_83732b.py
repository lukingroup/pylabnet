from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_output_on(self):
        return self._module.output_on()

    def exposed_output_off(self):
        return self._module.output_off()

    def exposed_set_freq(self, freq):
        return self._module.set_freq(freq)

    def exposed_set_power(self, power):
        return self._module.set_power(power)


class Client(ClientBase):

    def output_on(self):
        """ Turn output on """

        return self._service.exposed_output_on()

    def output_off(self):
        """ Turn output off """

        return self._service.exposed_output_off()

    def set_freq(self, freq):
        """ Sets power of MW source

        :param freq: (float) output frequency in Hz
        """

        return self._service.exposed_set_freq(freq)

    def set_power(self, power):
        """ Sets power of MW source

        :param power: (float) output power to set in dBm
        """

        return self._service.exposed_set_power(power)
