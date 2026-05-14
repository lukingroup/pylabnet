
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_is_laser_on(self):
        return self._module.is_laser_on()

    def exposed_turn_on(self):
        return self._module.turn_on()

    def exposed_turn_off(self):
        return self._module.turn_off()

    def exposed_set_current(self, current):
        return self._module.set_current(current)

    def exposed_set_power(self, power):
        return self._module.set_current(power)

    def exposed_set_wavelength(self, wavelength):
        return self._module.set_wavelength(wavelength)

    def exposed_get_wavelength(self):
        return self._module.get_wavelength()


class Client(ClientBase):

    def is_laser_on(self):
        return self._service.exposed_is_laser_on()

    def turn_on(self):
        return self._service.exposed_turn_on()

    def turn_off(self):
        return self._service.exposed_turn_off()

    def set_current(self, current):

        #current = pickle.dumps(current)

        return self._service.exposed_set_current(current)

    def set_power(self, power):

        #power = pickle.dumps(power)

        return self._service.exposed_set_power(power)

    def set_wavelength(self, wavelength):

        #wavelength = pickle.dumps(wavelength)

        return self._service.exposed_set_wavelength(wavelength)

    def get_wavelength(self):
        return self._service.exposed_get_wavelength()
