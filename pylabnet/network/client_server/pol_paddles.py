from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.polarization.polarization_control import Driver
import time

class Service(ServiceBase):

    def exposed_open(self):
        return self._module.open()

    def exposed_close(self):
        return self._module.close()
        
    def exposed_home(self, paddle):
        return self._module.home(paddle)

    def exposed_move(self, paddle, pos):
        return self._module.move(paddle)
       
    def exposed_move_rel(self, paddle, step):
        return self._module.move_rel(paddle, step)

    def exposed_get_angle(self, paddle):
        return self._module.get_angle(paddle)


class Client(ClientBase):

    def open(self):
        return self._service.exposed_open()

    def close(self):
        return self._service.exposed_close()

    def home(self, paddle):
        return self._service.exposed_home(paddle)

    def move(self, paddle, pos):
        return self._service.exposed_move(paddle,pos)
       
    def move_rel(self, paddle, step):
        return self._service.exposed.move_rel(paddle, step)

    def exposed_get_angle(self, paddle):
        return self._service.exposed.get_angle(paddle)

    


    