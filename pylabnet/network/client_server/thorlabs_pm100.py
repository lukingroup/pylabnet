from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_get_power(self):
        return self._module.get_power()

    def exposed_get_wavelength(self):
        return self._module.get_wavelength()

    def exposed_get_range(self):
        return self._module.get_range()

    def exposed_set_wavelength(self, wavelength):
        return self._module.set_wavelength(wavelength)

    def exposed_set_range_auto(self):
        return self._module.set_range_auto()


class Client(ClientBase):

    def get_power(self):
        return self._service.exposed_get_power()

    def get_wavelength(self):
        return self._service.exposed_get_wavelength()

    def get_range(self):
        return self._service.exposed_get_range()

    def set_wavelength(self, wavelength):
        return self._service.exposed_set_wavelength(wavelength)

    def set_range_auto(self):
        return self._service.exposed_set_range_auto()
