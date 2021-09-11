from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.nanopositioners.smaract import MCS2


class Service(ServiceBase):

    def exposed_close(self):
        return self._module.close()

    def exposed_set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        return self._module.set_parameters(
            channel, mode=mode, frequency=frequency, amplitude=amplitude, dc_vel=dc_vel
        )

    def exposed_get_voltage(self, channel):
        return self._module.get_voltage(channel)

    def exposed_set_voltage(self, channel, voltage=50):
        return self._module.set_voltage(channel, voltage=voltage)

    def exposed_n_steps(self, channel, n=1):
        return self._module.n_steps(channel, n=n)

    def exposed_move(self, channel, backward=False):
        return self._module.move(channel, backward)

    def exposed_stop(self, channel):
        return self._module.stop(channel)

    def exposed_is_moving(self, channel):
        return self._module.is_moving(channel)


class Client(ClientBase):

    def close(self):
        return self._service.exposed_close()

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        return self._service.exposed_set_parameters(
            channel, mode=mode, frequency=frequency, amplitude=amplitude, dc_vel=dc_vel
        )

    def get_voltage(self, channel):
        return self._service.exposed_get_voltage(channel)

    def set_voltage(self, channel, voltage=50):
        return self._service.exposed_set_voltage(channel, voltage=voltage)

    def n_steps(self, channel, n=1):
        return self._service.exposed_n_steps(channel, n=n)

    def move(self, channel, backward=False):
        return self._service.exposed_move(channel, backward=backward)

    def stop(self, channel):
        return self._service.exposed_stop(channel)

    def is_moving(self, channel):
        return self._service.exposed_is_moving(channel)
