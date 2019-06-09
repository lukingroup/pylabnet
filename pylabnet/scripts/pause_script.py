from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class PauseService(ServiceBase):
    def exposed_pause(self):
        return self._module.pause()


class PauseClient(ClientBase):
    def pause(self):
        return self._service.exposed_pause()
