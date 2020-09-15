from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_pause(self):
        return self._module.pause()

    def exposed_clear(self):
        return self._module.clear()

    def exposed_save(self):
        return self._module.save()


class Client(ClientBase):

    def pause(self):
        """ Pauses the go/run loop. 

        NOTE: does not actually stop counter acquisition! 
        There does not seem to be a way to do that from SI-TT API
        """

        return self._service.exposed_pause()

    def clear(self):
        """ Clears the data """

        return self._service.exposed_clear()

    def save(self):
        """ Saves the current data """

        return self._service.exposed_save()
