from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.nanopositioners.attocube import ANC300


class Service(ServiceBase):

    def exposed_ground(self, channel):
        return self._module.ground(channel)

    def exposed_set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        return self._module.set_parameters(
            channel, mode=mode, frequency=frequency, amplitude=amplitude, dc_vel=dc_vel
        )

    def exposed_get_step_voltage(self, channel):
        return self._module.get_step_voltage(channel)

    def exposed_set_step_voltage(self, channel, voltage):
        return self._module.set_step_voltage(channel, voltage=voltage)

    def exposed_get_step_frequency(self, channel):
        return self._module.get_step_frequency(channel)

    def exposed_set_step_frequency(self, channel, freq):
        return self._module.set_step_frequency(channel=channel, freq=freq)

    def exposed_get_capacitance(self, channel):
        return self._module.get_capacitance(channel=channel)

    def exposed_n_steps(self, channel, n=1):
        return self._module.n_steps(channel, n=n)

    def exposed_move(self, channel, backward=False):
        return self._module.move(channel, backward)

    def exposed_stop(self, channel):
        return self._module.stop(channel)

    def exposed_is_moving(self, channel):
        return self._module.is_moving(channel)

    def exposed_ground_all(self):
        return self._module.ground_all()

    def exposed_stop_all(self):
        return self._module.stop_all()

    def exposed_set_offset_voltage(self, channel, voltage):
        return self._module.set_offset_voltage(channel, voltage)

    def exposed_get_offset_voltage(self, channel):
        return self._module.get_offset_voltage(channel)


class Client(ClientBase):

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        return self._service.exposed_set_parameters(
            channel, mode=mode, frequency=frequency, amplitude=amplitude, dc_vel=dc_vel
        )

    def ground(self, channel):
        return self._service.exposed_ground(channel=channel)

    def get_step_voltage(self, channel):
        return self._service.exposed_get_step_voltage(channel)

    def set_step_voltage(self, channel, voltage):
        return self._service.exposed_set_step_voltage(channel, voltage=voltage)

    def get_step_frequency(self, channel):
        return self._service.exposed_get_step_frequency(channel)

    def set_step_frequency(self, channel, freq):
        return self._service.exposed_set_step_frequency(channel=channel, freq=freq)

    def get_capacitance(self, channel):
        return self._service.exposed_get_capacitance(channel=channel)

    def n_steps(self, channel, n=1):
        return self._service.exposed_n_steps(channel, n=n)

    def move(self, channel, backward=False):
        return self._service.exposed_move(channel, backward=backward)

    def stop(self, channel):
        return self._service.exposed_stop(channel)

    def is_moving(self, channel):
        return self._service.exposed_is_moving(channel)

    def ground_all(self):
        return self._service.exposed_ground_all()

    def stop_all(self):
        return self._service.exposed_stop_all()

    def set_offset_voltage(self, channel, voltage):
        return self._service.exposed_set_offset_voltage(channel, voltage)

    def get_offset_voltage(self, channel):
        return self._service.exposed_get_offset_voltage(channel)
