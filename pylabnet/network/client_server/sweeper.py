from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.sweeper import Sweep1D, MultiChSweep1D


class Service(ServiceBase):

    def exposed_stop(self):
        return self._module.stop()


class Client(ClientBase):
    
    def stop(self):
        return self._service.exposed_stop()
