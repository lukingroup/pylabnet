from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.scripts.sweeper.sweeper import Sweep1D, MultiChSweep1D


class Service(ServiceBase):

    def exposed_stop(self):
        return self._module.stop()

    def exposed_set_reps(self, reps=1):
        return self._module.set_reps(reps=reps)


class Client(ClientBase):

    def stop(self):
        return self._service.exposed_stop()

    def set_reps(self, reps=1):
        return self._service.exposed_set_reps(reps=reps)
