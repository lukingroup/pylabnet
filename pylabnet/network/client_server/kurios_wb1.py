from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_get_wavelength(self):
        return self._module.get_wavelength()

    def exposed_set_wavelength(self, wavelength):
        return self._module.set_wavelength(wavelength)

    def exposed_get_output(self):
        return self._module.get_output()

    def exposed_set_output(self, output):
        return self._module.set_output(output)

    def exposed_get_range(self):
        return self._module.get_range()


class Client(ClientBase):

    def get_wavelength(self):
        return self._service.exposed_get_wavelength()

    def set_wavelength(self, wavelength):
        return self._service.exposed_set_wavelength(wavelength)

    def get_output(self):
        return self._service.exposed_get_output()

    def set_output(self, output):
        return self._service.exposed_set_output(output)

    def get_range(self):
        return self._service.exposed_get_range()
