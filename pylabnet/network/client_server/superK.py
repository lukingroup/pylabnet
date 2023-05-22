import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    def exposed_emission_on(self, ):
        return self._module.emission_on()
    def exposed_emission_off(self, ):
        return self._module.emission_off()
    def exposed_read_power(self, ):
        return self._module.read_power()
    def exposed_set_power(self, power):
        return self._module.set_power(power)


class Client(ClientBase):
    def emission_on(self):
        return self._service.exposed_emission_on()
    def emission_off(self):
        return self._service.exposed_emission_off()
    def read_power(self):
        return self._service.exposed_read_power()
    def set_power(self, power):
        return self._service.exposed_set_power(power)