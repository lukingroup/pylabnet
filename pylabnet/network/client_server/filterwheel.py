
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
import pickle


class Service(ServiceBase):

    def exposed_change_filter(self, new_pos, protect_shutter_client):
        return self._module.change_filter(new_pos, protect_shutter_client)

    def exposed_get_pos(self):
        return self._module.get_pos()

    def exposed_get_filter_dict(self):
        return pickle.dumps(self._module.get_filter_dict())

    def exposed_get_name(self):
        return self._module.get_name()


class Client(ClientBase):
    def change_filter(self, new_pos, protect_shutter_client=None):
        return self._service.exposed_change_filter(new_pos, protect_shutter_client)

    def get_pos(self):
        return self._service.exposed_get_pos()

    def get_filter_dict(self):
        return pickle.loads(self._service.exposed_get_filter_dict())

    def get_name(self):
        return self._service.exposed_get_name()
