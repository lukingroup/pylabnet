from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_get_channel(self):
        return self._module.get_channel()

    def exposed_set_channel(self, ch):
        return self._module.set_channel(ch)

    def exposed_get_power(self, ch):
        return self._module.get_power(ch)

    def exposed_get_unit(self, ch):
        return self._module.get_unit(ch)

    def exposed_set_unit(self, ch, unit_str):
        return self._module.set_unit(ch, unit_str)

    def exposed_get_wavelength(self, ch):
        return self._module.get_wavelength(ch)

    def exposed_set_wavelength(self, ch, wavelength):
        return self._module.set_wavelength(ch, wavelength)

    def exposed_get_auto(self, ch):
        return self._module.get_auto(ch)

    def exposed_set_auto(self, ch, auto):
        return self._module.set_auto(ch, auto)

    def exposed_get_range(self, ch):
        return self._module.get_range(ch)

    def exposed_set_range(self, ch, range):
        return self._module.set_range(ch, range)


class Client(ClientBase):

    def get_channel(self):
        return self._service.exposed_get_channel()

    def set_channel(self, ch):
        return self._service.exposed_set_channel(ch)

    def get_power(self, ch):
        return self._service.exposed_get_power(ch)

    def get_unit(self, ch):
        return self._service.exposed_get_unit(ch)

    def set_unit(self, ch, unit_str):
        return self._service.exposed_set_unit(ch, unit_str)

    def get_wavelength(self, ch):
        return self._service.exposed_get_wavelength(ch)

    def set_wavelength(self, ch, wavelength):
        return self._service.exposed_set_wavelength(ch, wavelength)

    def get_auto(self, ch):
        return self._service.exposed_get_auto(ch)

    def set_auto(self, ch, auto):
        return self._service.exposed_set_auto(ch, auto)

    def get_range(self, ch):
        return self._service.exposed_get_range(ch)

    def set_range(self, ch, range):
        return self._service.exposed_set_range(ch, range)
