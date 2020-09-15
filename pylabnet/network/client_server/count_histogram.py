from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_pause(self):
        return self._module.pause()

    def exposed_clear(self):
        return self._module.clear()


class Client(ClientBase):

    def pause(self):
        """ Pauses the go/run loop. 

        NOTE: does not actually stop counter acquisition! 
        There does not seem to be a way to do that from SI-TT API
        """

        self._service.exposed_pause()

    def clear(self):
        """ Clears the data """

        self._service.exposed_clear()
