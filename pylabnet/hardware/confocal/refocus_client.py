from pylabnet.core.client_base import ClientBase


class RefocusClient(ClientBase):
    def rfcs(self):
        return self._service.exposed_refocus()
