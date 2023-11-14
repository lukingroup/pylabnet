
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_get_ai_voltage(self, ai_channel, range):
        return self._module.get_ai_voltage(
            ai_channel=ai_channel,
            range=range
        )


class Client(ClientBase):

    def get_ai_voltage(self, ai_channel, range=1):
        return self._service.exposed_get_ai_voltage(
            ai_channel=ai_channel,
            range=range
        )
