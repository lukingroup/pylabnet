from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase

class Driver:
    """
    Handles the "device" functions. This is directly interfaced by the device server.
    """

    def __init__(self, logger, init_value=None):
        self.logger = logger

        if init_value is None:
            init_value = {1: 2, 2: 100}
        self.value = init_value

    def up_function(self, ch):
        self.value[ch] *= 2
        self.logger.info(f"The value of Channel {ch} is now {self.value[ch]}")

    def down_function(self, ch):
        self.value[ch] /= 2
        self.logger.info(f"The value of Channel {ch} is now {self.value[ch]}")

    def set_value_function(self, value, ch):
        try:
            self.value[ch] = float(value)
        except ValueError:
            self.logger.error(f"Invalid value {value} provided.")
        self.logger.info(f"The value of Channel {ch} is now {self.value[ch]}")

class Service(ServiceBase):
    """
    Interfaces with the device by directly calling the device driver functions. Listens for commands from clients that use the exposed wrapper functions.
    """
    def exposed_up_function(self, ch):
        """
        Wrapper function that clients call. This then goes on to call the driver function that connects to the device. """
        return self._module.up_function(ch)

    def exposed_down_function(self, ch):
        return self._module.down_function(ch)

    def exposed_set_value_function(self, value, ch):
        return self._module.set_value_function(value, ch)

class Client(ClientBase):
    """
    Connects to the device server. Gives commands by calling the wrapper functions that are exposed by the server, so it does not have direct access to the driver functions.
    """
    def up_function(self, ch):
        """
        Function for client users to call. This calls a wrapper function exposed by the server which is itself also a wrapper for the driver.
        """
        return self._service.exposed_up_function(ch)

    def down_function(self, ch):
        return self._service.exposed_down_function(ch)

    def set_value_function(self, value, ch):
        return self._service.exposed_set_value_function(value, ch)
