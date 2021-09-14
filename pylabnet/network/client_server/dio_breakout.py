
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_measure_voltage(self, board, channel):
        return self._module.measure_voltage(board, channel)

    def exposed_set_high_voltage(self, board, channel, voltage):
        return self._module.set_high_voltage(board, channel, voltage)

    def exposed_set_low_voltage(self, board, channel, voltage):
        return self._module.set_low_voltage(board, channel, voltage)

    def exposed_get_high_voltage(self, board, channel):
        return self._module.get_high_voltage(board, channel)

    def exposed_get_low_voltage(self, board, channel):
        return self._module.get_low_voltage(board, channel)

    def exposed_save(self):
        return self._module.save()

    def exposed_override(self, board, channel, state=True):
        return self._module.override(board, channel, state)

    def exposed_disable_override(self, board, channel):
        return self._module.disable_override(board, channel)

    def close_server(self):
        """ Closes the server for which the service is running

        Overwrites parent class method
        """

        self._module.close()

        super().close_server()


class Client(ClientBase):

    def measure_voltage(self, board, channel):
        return self._service.exposed_measure_voltage(board, channel)

    def set_high_voltage(self, board, channel, voltage):
        return self._service.exposed_set_high_voltage(board, channel, voltage)

    def set_low_voltage(self, board, channel, voltage):
        return self._service.exposed_set_low_voltage(board, channel, voltage)

    def get_high_voltage(self, board, channel):
        return self._service.exposed_get_high_voltage(board, channel)

    def get_low_voltage(self, board, channel):
        return self._service.exposed_get_low_voltage(board, channel)

    def save(self):
        return self._service.exposed_save()

    def override(self, board, channel, state=True):
        return self._service.exposed_override(board, channel, state)

    def disable_override(self, board, channel):
        return self._service.exposed_disable_override(board, channel)
