from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_instrument_mode(self, modeint):
        return self._module.set_instrument_mode(modeint)

    def exposed_get_instrument_mode(self):
        return self._module.get_instrument_mode()

    def exposed_set_wavelength(self, wavelength):
        return self._module.set_wavelength(wavelength)

    def exposed_get_wavelength(self):
        return self._module.get_wavelength()

    def exposed_set_scanrate(self, scanrate):
        return self._module.set_scanrate(scanrate)

    def exposed_get_scanrate(self):
        return self._module.get_scanrate()

    def exposed_measure_polarization(self):
        return self._module.measure_polarization()

    def exposed_get_power(self):
        return self._module.get_power()


class Client(ClientBase):

    def set_instrument_mode(self, modeint):
        return self._service.exposed_set_instrument_mode(modeint)

    def get_instrument_mode(self):
        return self._service.exposed_get_instrument_mode()

    def set_wavelength(self, wavelength):
        return self._service.exposed_set_wavelength(wavelength)

    def get_wavelength(self):
        return self._service.exposed_get_wavelength()

    def set_scanrate(self, scanrate):
        return self._service.exposed_set_scanrate(scanrate)

    def get_scanrate(self):
        return self._service.exposed_get_scanrate()

    def measure_polarization(self):
        return self._service.exposed_measure_polarization()

    def get_power(self):
        return self._service.exposed_get_power()
