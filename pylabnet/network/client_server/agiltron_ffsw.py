from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_output(self, ch):
        return self._module.set_output(ch)


class Client(ClientBase):

    def set_output(self, ch):
        return self._service.exposed_set_output(ch)
