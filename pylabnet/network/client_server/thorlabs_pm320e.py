from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase

class Service(ServiceBase):

    def exposed_get_power(self, channel):
        return self._module.get_power(channel)


class Client(ClientBase):

    def get_power(self, channel):
        return self._service.exposed_get_power(channel)
