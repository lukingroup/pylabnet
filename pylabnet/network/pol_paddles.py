from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.nanopositioners.smaract import polarization_control

class Service(ServiceBase):

    def exposed_close(self):
        return self._module.close()

  
class Client(ClientBase):

    def close(self):
        return self._service.exposed_close()

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        return self._service.exposed_set_parameters(
            channel, mode=mode, frequency=frequency, amplitude=amplitude, dc_vel=dc_vel
        )

  