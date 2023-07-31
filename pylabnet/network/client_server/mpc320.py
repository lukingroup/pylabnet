
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_home(self):
        return self._module.home()

    def exposed_set_velocity(self, velocity):
        return self._module.set_velocity(velocity=velocity)

    def exposed_move(self, paddle_num, pos, sleep_time=0.1):
        res = self._module.move(paddle_num, pos, sleep_time)

    def exposed_move_rel(self, paddle_num, step, sleep_time=0.1):
        return self._module.move_rel(paddle_num, step, sleep_time)

    def exposed_get_angle(self):
        return self._module.get_angle()


class Client(ClientBase):

    def home(self):
        return self._service.exposed_home()

    def set_velocity(self):
        return self._service.exposed_set_velocity()

    def move(self):
        return self._service.exposed_move()

    def move_rel(self):
        return self._service.exposed_move_rel()

    def get_angle(self):
        return self._service.exposed_get_angle()
