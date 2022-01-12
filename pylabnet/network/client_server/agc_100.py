from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_get_pressure(self):
        return self._module.get_pressure()

class Client(ClientBase):

    def get_pressure(self):
        """ Get presure in mBar """

        return self._service.exposed_get_pressure()