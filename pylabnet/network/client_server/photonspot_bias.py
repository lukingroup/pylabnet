from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_delatch(self, ch):
        return self._module.delatch(ch)

    def exposed_set_zero(self, ch):
        return self._module.set_zero(ch)

    def exposed_set_bias(self, ch, bias_current):
        return self._module.set_bias(ch, bias_current)

    def exposed_ramp_up(self, ch, target_bias, init_bias=0.0):
        return self._module.ramp_up(ch, target_bias, init_bias)


class Client(ClientBase):

    def delatch(self, ch):
        return self._service.exposed_delatch(ch)

    def set_zero(self, ch):
        return self._service.exposed_set_zero(ch)

    def set_bias(self, ch, bias_current):
        return self._service.exposed_set_bias(ch, bias_current)

    def ramp_up(self, ch, target_bias, init_bias=0.0):
        return self._service.exposed_ramp_up(ch, target_bias, init_bias)
