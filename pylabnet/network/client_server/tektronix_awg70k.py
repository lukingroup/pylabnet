
import numpy as np

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_query(self, command):
        return self._module.device.query(command)

    def exposed_write(self, command):
        return self._module.device.write(command)

    def exposed_set_output_state(self, ch, state):
        return self._module.set_output_state(ch, state)

    def exposed_get_output_state(self, ch):
        return self._module.get_output_state(ch)

    def exposed_run(self):
        return self._module.run()

    def exposed_stop(self):
        return self._module.stop()

    def exposed_get_output_state(self):
        return self._module.get_output_state()


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def query(self, command):
        return self._service.exposed_query(command)

    def write(self, command):
        return self._service.exposed_write(command)

    def set_output_state(self, ch, state):
        return self._service.exposed_set_output_state(ch, state)

    def get_output_state(self, ch):
        return self._service.exposed_get_output_state(ch)

    def run(self):
        return self._service.exposed_run()

    def stop(self):
        return self._service.exposed_stop()

    def get_output_state(self):
        return self._service.exposed_get_output_state()
