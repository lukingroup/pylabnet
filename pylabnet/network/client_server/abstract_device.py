from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase

class Driver:
    """
    Handles the "device" functions. This is directly interfaced by the device server.
    """

    def __init__(self, logger, init_value):
        self.logger = logger
        self.value = init_value

    def up_function(self):
        self.value *= 2
        self.logger.info(f"The value is now {self.value}")

    def down_function(self):
        self.value /= 2
        self.logger.info(f"The value is now {self.value}")

    def set_value_function(self, value):
        try:
            self.value = float(value)
        except ValueError:
            self.logger.error(f"Invalid value {value} provided.")
            self.value = 2
        self.logger.info(f"The value is now {self.value}")

class Service(ServiceBase):
    """
    Interfaces with the device by directly calling the device driver functions. Listens for commands from clients that use the exposed wrapper functions.
    """
    def exposed_up_function(self):
        """
        Wrapper function that clients call. This then goes on to call the driver function that connects to the device. """
        return self._module.up_function()

    def exposed_down_function(self):
        return self._module.down_function()

    def exposed_set_value_function(self, value):
        return self._module.set_value_function(value)

class Client(ClientBase):
    """
    Connects to the device server. Gives commands by calling the wrapper functions that are exposed by the server, so it does not have direct access to the driver functions.
    """
    def up_function(self):
        """
        Function for client users to call. This calls a wrapper function exposed by the server which is itself also a wrapper for the driver.
        """
        return self._service.exposed_up_function()

    def down_function(self):
        return self._service.exposed_down_function()

    def set_value_function(self, value):
        return self._service.exposed_set_value_function(value)
