import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_is_laser_on(self, laser_num=1):
        return self._module.is_laser_on(laser_num)

    def exposed_turn_on(self, laser_num=1):
        return self._module.turn_on(laser_num)

    def exposed_turn_off(self, laser_num=1):
        return self._module.turn_off(laser_num)

    def exposed_voltage(self, laser_num):
        return self._module.voltage(laser_num)

    def exposed_set_voltage(self, voltage, laser_num):
        voltage = pickle.loads(voltage)
        return self._module.set_voltage(voltage, laser_num)

    def exposed_current_sp(self, laser_num):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        return self._module.current_sp(laser_num)

    def exposed_current_act(self, laser_num):
        """ Gets measured current

        :return: (float) value of actual current
        """

        return self._module.current_sp(laser_num)

    def exposed_set_current(self, current, laser_num):
        """ Sets the current to desired value

        :param current: (float) value of current to set as setpoint
        """

        current = pickle.loads(current)
        return self._module.set_current(current, laser_num)

    def exposed_temp_sp(self, laser_num):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        return self._module.temp_sp(laser_num)

    def exposed_temp_act(self, laser_num):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        return self._module.temp_act(laser_num)

    def exposed_set_temp(self, temp, laser_num):
        """ Sets the current to desired value

        :param temp: (float) value of temperature to set to in Celsius
        """

        temp = pickle.loads(temp)
        return self._module.set_temp(temp, laser_num)

    def exposed_configure_scan(self, offset=65, amplitude=100, frequency=0.2, laser_num=1):
        """ Sets the scan parameters for piezo scanning

        :param offset: (float) scan offset (center value) in volts (between 0 and 130)
        :param amplitude: (float) scan amplitude (peak to peak) in volts
        """

        return self._module.configure_scan(offset, amplitude, frequency, laser_num)

    def exposed_start_scan(self, laser_num=1):
        """ Starts a piezo scan """

        return self._module.start_scan(laser_num)

    def exposed_stop_scan(self, laser_num=1):
        """ Stops piezo scan """

        return self._module.stop_scan(laser_num)



class Client(ClientBase):

    def is_laser_on(self, laser_num=1):
        return self._service.exposed_is_laser_on(laser_num)

    def turn_on(self, laser_num=1):
        return self._service.exposed_turn_on(laser_num)

    def turn_off(self, laser_num=1):
        return self._service.exposed_turn_off(laser_num)

    def voltage(self, laser_num=1):
        return self._service.exposed_voltage(laser_num)

    def set_voltage(self, voltage, laser_num=1):
        voltage = pickle.dumps(voltage)
        return self._service.exposed_set_voltage(voltage, laser_num)

    def set_ao_voltage(self, ao_channel=1, voltages=[0]):
        """ Wrapper for using this in generic AO context

        :param ao_channel: (
        :param voltages: (list) list containing one element, the voltage to set
        """

        voltage = pickle.dumps(voltages[0])
        return self._service.exposed_set_voltage(voltage, ao_channel)

    def current_sp(self, laser_num):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        return self._service.exposed_current_sp(laser_num)

    def current_act(self, laser_num):
        """ Gets measured current

        :return: (float) value of actual current
        """

        return self._service.exposed_current_act(laser_num)

    def set_current(self, current, laser_num):
        """ Sets the current to desired value

        :param current: (float) value of current to set as setpoint
        """

        current = pickle.dumps(current, laser_num)
        return self._service.exposed_set_current(current, laser_num)

    def temp_sp(self, laser_num=1):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        return self._service.exposed_temp_sp(laser_num)

    def temp_act(self, laser_num=1):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        return self._service.exposed_temp_act(laser_num)

    def set_temp(self, temp, laser_num=1):
        """ Sets the current to desired value

        :param temp: (float) value of temperature to set to in Celsius
        """

        temp = pickle.dumps(temp, laser_num)
        return self._service.exposed_set_temp(temp, laser_num)

    def configure_scan(self, offset=65, amplitude=100, frequency=0.2, laser_num=1):
        """ Sets the scan parameters for piezo scanning

        :param offset: (float) scan offset (center value) in volts (between 0 and 130)
        :param amplitude: (float) scan amplitude (peak to peak) in volts
        :param frequency: (float) scan frequency (Hz)
        """

        return self._service.exposed_configure_scan(offset, amplitude, frequency, laser_num)

    def start_scan(self, laser_num=1):
        """ Starts a piezo scan """

        return self._service.exposed_start_scan(laser_num)

    def stop_scan(self, laser_num=1):
        """ Stops piezo scan """

        return self._service.exposed_stop_scan(laser_num)
