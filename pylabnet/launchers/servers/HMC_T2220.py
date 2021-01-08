from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_output_on(self):
        return self._module.output_on()

    def exposed_output_off(self):
        return self._module.output_off()

    def exposed_check_power_out_of_range(self):
        return self._module.check_power_out_of_range()

    def exposed_is_output_on(self):
        return self._module.is_output_on()

    def exposed_set_freq(self, freq):
        return self._module.set_freq(freq)

    def exposed_get_freq(self):
        return self._module.get_freq()

    def exposed_set_power(self, power):
        return self._module.set_power(power)

    def exposed_get_power(self):
        return self._module.get_power()


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def output_on(self):
        return self._service.exposed_output_on()

    def output_off(self):
        return self._service.exposed_output_off()

    def check_power_out_of_range(self):
        return self._service.exposed_check_power_out_of_range()

    def is_output_on(self):
        return self._service.exposed_is_output_on()

    def set_freq(self, freq):
        return self._service.exposed_set_freq(freq)

    def get_freq(self):
        return self._service.exposed_get_freq()

    def set_power(self, power):
        return self._service.exposed_set_power(power)

    def get_power(self):
        return self._service.exposed_get_power()
