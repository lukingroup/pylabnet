from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_turn_on(self, device_id):
        return self._module.turn_on(device_id)

    def exposed_turn_off(self, device_id):
        return self._module.turn_off(device_id)

    def exposed_is_on(self, device_id):
        return self._module.is_on(device_id)

class Client(ClientBase):

    def turn_on(self, device_id):
        return self._service.exposed_turn_on(device_id)

    def turn_off(self, device_id):
        return self._service.exposed_turn_off(device_id)

    def is_on(self, device_id):
        return self._service.exposed_is_on(device_id)