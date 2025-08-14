from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_output_on(self, ch):
        return self._module.output_on(ch)

    def exposed_output_off(self, ch):
        return self._module.output_off(ch)


class Client(ClientBase):

    def output_on(self, ch):
        return self._service.exposed_output_on(ch)

    def output_off(self, ch):
        return self._service.exposed_output_off(ch)
