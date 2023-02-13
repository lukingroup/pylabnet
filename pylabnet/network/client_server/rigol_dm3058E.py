
import numpy as np
import matplotlib.pyplot as plt

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase

class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_set_resistance_measurement(self):
        return self._module.set_resistance_measurement()

    def exposed_set_resistance_range(self):
        return self._module.set_resistance_range()

    def exposed_get_resistance(self, db):
        return self._module.get_resistance(db)

  
class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def set_resistance_measurement(self):
        return self._service.exposed_set_resistance_measurement()

    def set_resistance_range(self):
        return self._service.exposed_set_resistance_range()

    def get_resistance(self, db):
        return self._service.exposed_get_resistance(db)

   