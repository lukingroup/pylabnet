from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class PauseFlag:
    def __init__(self):
        self.is_running = False

    def pause(self):
        self.is_running = False
        return 0


class PauseService(ServiceBase):
    def exposed_pause(self):

        if isinstance(self._module, list):
            for module in self._module:
                module.pause()
            return 0

        else:
            return self._module.pause()


class PauseClient(ClientBase):
    def pause(self):
        return self._service.exposed_pause()
