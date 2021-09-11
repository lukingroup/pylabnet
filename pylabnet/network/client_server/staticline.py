
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_up(self):
        return self._module.up()

    def exposed_down(self):
        return self._module.down()

    def exposed_get_name(self):
        return self._module.get_name()


class Client(ClientBase):

    def up(self):
        return self._service.exposed_up()

    def down(self):
        return self._service.exposed_down()

    def get_name(self):
        return self._service.exposed_get_name()
