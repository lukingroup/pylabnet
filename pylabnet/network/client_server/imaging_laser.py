
import pickle
import numpy as np
import matplotlib.pyplot as plt

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_turn_laser_off(self):
        return self._module.turn_laser_off()

    def exposed_turn_laser_on(self):
        return self._module.turn_laser_on()

    def exposed_set_current(self, amps):
        return self._module.set_current(amps)

    def exposed_query(self, command):
        query = self._module.device.query(command)
        return pickle.dumps(query)

    def exposed_write(self, command):
        return self._module.device.write(command)


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def turn_laser_off(self):
        return self._service.exposed_turn_laser_off()

    def turn_laser_on(self):
        return self._service.exposed_turn_laser_on()

    def set_current(self, amps):
        return self._service.exposed_set_current(amps)

    def query(self, command):
        pickled_query = self._service.exposed_query(command)
        return pickle.loads(pickled_query)

    def write(self, command):
        return self._service.exposed_write(command)
