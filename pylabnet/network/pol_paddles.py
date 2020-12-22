from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.power_meter.thorlabs_pm320e import Driver
from pylabnet.hardware.polarization.polarization_control import MPC320
import time

class Service(ServiceBase):

    def exposed_open(self, device):
        return self._module.open(device)

    def exposed_close(self, device):
        return self._module.close(device)
        
    def exposed_home(self, device, paddle):
        return self._module.home(device, paddle)

    def exposed_move(self, device, paddle, pos):
        return self._module.move(device, paddle)
       
    def exposed_move_rel(self, device, paddle, step):
        return self._module.move_rel(device, paddle, step)

    def exposed_get_angle(self, device, paddle):
        return self._module.get_angle(device, paddle)


class Client(ClientBase):

    def open(self):
        return self._service.exposed_open(device)

    def close(self):
        return self._service.exposed_close(device)

    def home(self, device, paddle):
        return self._service.exposed_home(device, paddle)

    def move(self, device, paddle, pos):
        return self._service.exposed_move(device, paddle,pos)
       
    def move_rel(self, device, paddle, step):
        return self._service.exposed.move_rel(device, paddle, step)

    def exposed_get_angle(self, device, paddle):
        return self._service.exposed.get_angle(device, paddle)

    


    