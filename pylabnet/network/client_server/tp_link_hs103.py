from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_turn_on(self, channel_id):
        return self._module.turn_on(channel_id)

    def exposed_turn_off(self, channel_id):
        return self._module.turn_off(channel_id)

    def exposed_is_on(self, channel_id):
        return self._module.is_on(channel_id)

class Client(ClientBase):

    def turn_on(self, channel_id):
        return self._service.exposed_turn_on(channel_id)

    def turn_off(self, channel_id):
        return self._service.exposed_turn_off(channel_id)

    def is_on(self, channel_id):
        return self._service.exposed_is_on(channel_id)