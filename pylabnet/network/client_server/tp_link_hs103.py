from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_turn_on(self):
        return self._module.turn_on()

    def exposed_turn_off(self):
        return self._module.turn_off()

    def exposed_is_on(self):
        return self._module.is_on()

class Client(ClientBase):

    def turn_on(self):
        return self._service.exposed_turn_on()

    def turn_off(self):
        return self._service.exposed_turn_off()

    def is_on(self):
        return self._service.exposed_is_on()