import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_is_laser_on(self):
        return self._module.is_laser_on()

    def exposed_turn_on(self):
        return self._module.turn_on()

    def exposed_turn_off(self):
        return self._module.turn_off()

    def exposed_voltage(self):
        return self._module.voltage()

    def exposed_set_voltage(self, voltage):
        voltage = pickle.loads(voltage)
        return self._module.set_voltage(voltage)


class Client(ClientBase):

    def is_laser_on(self):
        return self._service.exposed_is_laser_on()

    def turn_on(self):
        return self._service.exposed_turn_on()

    def turn_off(self):
        return self._service.exposed_turn_off()

    def voltage(self):
        return self._service.exposed_voltage()

    def set_voltage(self, voltage):
        voltage = pickle.dumps(voltage)
        return self._service.exposed_set_voltage(voltage)

    def set_ao_voltage(self, ao_channel=[], voltages=[0]):
        """ Wrapper for using this in generic AO context

        :param ao_channel: (list) completely irrelevant
        :param voltages: (list) list containing one element, the voltage to set
        """

        voltage = pickle.dumps(voltages[0])
        return self._service.exposed_set_voltage(voltage)