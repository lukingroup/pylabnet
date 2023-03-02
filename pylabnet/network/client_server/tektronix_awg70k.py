
import numpy as np

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_query(self, command):
        return self._module.query(command)

    def exposed_write(self, command):
        return self._module.write(command)

    def exposed_query_binary_values(self, command, **kwargs):
        return self._module.query_binary_values(command, **kwargs)

    def exposed_write_binary_values(self, command, data, **kwargs):
        return self._module.write_binary_values(command, data, **kwargs)


class Client(ClientBase):

    def query(self, command):
        return self._service.exposed_query(command)

    def write(self, command):
        return self._service.exposed_write(command)

    def query_binary_values(self, command, **kwargs):
        return self._service.exposed_query_binary_values(command, **kwargs)

    def write_binary_values(self, command, data, **kwargs):
        return self._service.exposed_write_binary_values(command, data, **kwargs)
