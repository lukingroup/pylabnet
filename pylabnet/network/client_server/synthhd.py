from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_output_on(self, channel=None):
        return self._module.output_on(channel=channel)

    def exposed_output_off(self, channel=None):
        return self._module.output_off(channel=channel)

    def exposed_set_freq(self, freq, channel=None):
        return self._module.set_freq(freq, channel=channel)

    def exposed_set_trigger(self, trigger_mode=None):
        return self._module.set_trigger(trigger_mode=trigger_mode)

    def exposed_set_power(self, power, channel=None):
        return self._module.set_power(power, channel=channel)

    def exposed_set_reference_mode(self, arg=None):
        return self._module.set_reference_mode(arg=arg)

    def exposed_set_external_reference_frequency(self, value=None):
        return self._module.set_external_reference_frequency(value=value)


class Client(ClientBase):

    def output_on(self, channel=None):
        """ Turn output on """

        return self._service.exposed_output_on(channel=channel)

    def output_off(self, channel=None):
        """ Turn output off """

        return self._service.exposed_output_off(channel=channel)

    def set_freq(self, freq, channel=None):
        """ Sets freq of MW source

        :param freq: (float) output frequency in Hz
        """

        return self._service.exposed_set_freq(freq, channel=channel)

    def set_trigger(self, trigger_mode):
        """ Sets trigger mode of MW source

        :param trigger mode: (str) trigger mode
            'disabled',
            'full frequency sweep',
            'single frequency step',
            'stop all',
            'rf enable',
            'remove interrupts',
            'reserved',
            'reserved',
            'am modulation',
            'fm modulation',
        """

        return self._service.exposed_set_trigger(trigger_mode=trigger_mode)

    def set_power(self, power, channel=None):
        """ Sets power of MW source

        :param power: (float) output power to set in dBm
        """

        return self._service.exposed_set_power(power, channel=channel)

    def set_reference_mode(self, arg=None):
        """Set frequency reference mode.

        Args:
            arg (str): mode
        """

        return self._service.exposed_set_reference_mode(arg=arg)

    def set_external_reference_frequency(self, value=None):
        """Set reference frequency in Hz.

        Args:
            value (float / int): frequency in Hz
        """

        return self._service.exposed_set_external_reference_frequency(value=value)
