from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_output_on(self, ch):
        return self._module.output_on(ch)

    def exposed_output_off(self, ch):
        return self._module.output_off(ch)

    def exposed_set_freq(self, ch, freq):
        return self._module.set_freq(ch, freq)

    def exposed_set_amp_vpp(self, ch, amp_vpp):
        return self._module.set_amp_vpp(ch, amp_vpp)


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def output_on(self, ch):
        return self._service.exposed_output_on(ch)

    def output_off(self, ch):
        return self._service.exposed_output_off(ch)

    def set_freq(self, ch, freq):
        return self._service.exposed_set_freq(ch, freq)

    def set_amp_vpp(self, ch, amp_vpp):
        return self._service.exposed_set_amp_vpp(ch, amp_vpp)
