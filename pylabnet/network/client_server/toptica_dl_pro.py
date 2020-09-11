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

    def exposed_current_sp(self):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        return self._module.current_sp()

    def exposed_current_act(self):
        """ Gets measured current

        :return: (float) value of actual current
        """

        return self._module.current_sp()
    
    def exposed_set_current(self, current):
        """ Sets the current to desired value
        
        :param current: (float) value of current to set as setpoint
        """

        current = pickle.loads(current)
        return self._module.set_current(current)

    def exposed_temp_sp(self):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        return self._module.temp_sp()

    def exposed_temp_act(self):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        return self._module.temp_act()

    def exposed_set_temp(self, temp):
        """ Sets the current to desired value
        
        :param temp: (float) value of temperature to set to in Celsius
        """

        temp = pickle.loads(temp)
        return self._module.set_temp(temp)

    def exposed_configure_scan(self, offset=65, amplitude=100, frequency=0.2):
        """ Sets the scan parameters for piezo scanning

        :param offset: (float) scan offset (center value) in volts (between 0 and 130)
        :param amplitude: (float) scan amplitude (peak to peak) in volts
        """

        return self._module.configure_scan(offset, amplitude, frequency)

    def exposed_start_scan(self):
        """ Starts a piezo scan """

        return self._module.start_scan()

    def exposed_stop_scan(self):
        """ Stops piezo scan """

        return self._module.stop_scan()



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

    def current_sp(self):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        return self._service.exposed_current_sp()

    def current_act(self):
        """ Gets measured current

        :return: (float) value of actual current
        """

        return self._service.exposed_current_act()
    
    def set_current(self, current):
        """ Sets the current to desired value
        
        :param current: (float) value of current to set as setpoint
        """

        current = pickle.dumps(current)
        return self._service.exposed_set_current(current)

    def temp_sp(self):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        return self._service.exposed_temp_sp()

    def temp_act(self):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        return self._service.exposed_temp_act()

    def set_temp(self, temp):
        """ Sets the current to desired value
        
        :param temp: (float) value of temperature to set to in Celsius
        """

        temp = pickle.dumps(temp)
        return self._service.exposed_set_temp(temp)

    def configure_scan(self, offset=65, amplitude=100, frequency=0.2):
        """ Sets the scan parameters for piezo scanning

        :param offset: (float) scan offset (center value) in volts (between 0 and 130)
        :param amplitude: (float) scan amplitude (peak to peak) in volts
        :param frequency: (float) scan frequency (Hz)
        """

        return self._service.exposed_configure_scan(offset, amplitude, frequency)

    def start_scan(self):
        """ Starts a piezo scan """

        return self._service.exposed_start_scan()

    def stop_scan(self):
        """ Stops piezo scan """

        return self._service.exposed_stop_scan()
        