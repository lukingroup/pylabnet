from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_output_on(self):
        return self._module.output_on()

    def exposed_output_off(self):
        return self._module.output_off()

    def exposed_set_frequency(self, freq):
        return self._module.set_frequency(freq)

    def exposed_set_power(self, power):
        return self._module.set_power(power)

    def exposed_set_rf_mode(self, rf_mode='single_tone'):
        return self._module.set_rf_mode(rf_mode)

    def exposed_get_frequency(self):
        return self._module.get_frequency()

    def exposed_get_power(self):
        return self._module.get_power()

    def exposed_get_status(self):
        return self._module.get_status()

    def exposed_get_temperature(self):
        return self._module.get_temperature()


class Client(ClientBase):

    def output_on(self):
        """ Turn output on """

        return self._service.exposed_output_on()

    def output_off(self):
        """ Turn output off """

        return self._service.exposed_output_off()

    def set_frequency(self, freq):
        """ Sets freq of MW source

        :param freq: (float) output frequency in Hz
        """

        return self._service.exposed_set_frequency(freq)

    def set_power(self, power):
        """ Sets power of MW source

        :param power: (float) output power to set in dBm
        """

        return self._service.exposed_set_power(power)

    def set_rf_mode(self, rf_mode):
        """ Sets RF mode

        :param rf_mode: (float) 'single_tone' or 'sweep'
        """

        return self._service.exposed_set_rf_mode(rf_mode)

    def get_frequency(self):
        """ gets freq of MW source

        :param freq: (float) output frequency in Hz
        """

        return self._service.exposed_get_frequency()

    def get_power(self):
        """ gets power of MW source

        :param power: (float) output power in dBm
        """

        return self._service.exposed_get_power()

    def get_status(self):
        """ gets status of MW source

        "on" or "off"
        """

        return self._service.exposed_get_status()

    def get_temperature(self):
        """ gets status of MW source

        "on" or "off"
        """

        return self._service.exposed_get_temperature()
