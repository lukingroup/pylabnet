from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase

class Service(ServiceBase):

    def exposed_get_power(self, channel):
        return self._module.get_power(channel)

    def exposed_get_wavelength(self, channel):
        return self._module.get_wavelength(channel)

    def exposed_get_range(self, channel):
        return self._module.get_range(channel)

    def exposed_set_wavelength(self, channel, wavelength):
        return self._module.set_wavelength(channel, wavelength)

    def exposed_set_range(self, channel, p_range):
        return self._module.set_range(channel, p_range)


class Client(ClientBase):

    def get_power(self, channel):
        return self._service.exposed_get_power(channel)

    def get_wavelength(self, channel):
        return self._service.exposed_get_wavelength(channel)

    def get_range(self, channel):
        return self._service.exposed_get_range(channel)

    def set_wavelength(self, channel, wavelength):
        return self._service.exposed_set_wavelength(channel, wavelength)

    def set_range(self, channel, p_range):
        return self._service.exposed_set_range(channel, p_range)
