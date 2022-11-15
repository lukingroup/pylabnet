
import numpy as np
import matplotlib.pyplot as plt

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_send_command(self, msg):
        return self._module.send_command(msg)

    def exposed_read_reply(self, length=200):
        return self._module.read_reply(length)

    def exposed_send_read(self, msg, length=200):
        return self._module.send_read(msg, length)

    def exposed_send_read_verify(self, msg, length=200):
        return self._module.send_read_verify(msg, length)

    def exposed_set_P(self, P):
        return self._module.set_P(P)

    def exposed_set_I(self, I):
        return self._module.set_I(I)

    def exposed_set_D(self, D):
        return self._module.set_D(D)

    def exposed_set_int_time(self, time):
        return self._module.set_int_time(time)

    def exposed_set_offset(self, offset):
        return self._module.set_offset(offset)

    def exposed_get_status(self):
        return self._module.get_status()

    def exposed_get_all_vals(self):
        return self._module.get_all_vals()

    def exposed_get_P(self):
        return self._module.get_P()

    def exposed_get_I(self):
        return self._module.get_I()

    def exposed_get_D(self):
        return self._module.get_D()

    def exposed_get_int_time(self):
        return self._module.get_int_time()

    def exposed_get_offset(self):
        return self._module.get_offset()

    def exposed_get_errorval(self):
        return self._module.get_errorval()

    def exposed_get_integrator(self):
        return self._module.get_integrator()

    def exposed_get_PID_output(self):
        return self._module.get_PID_output()

    def exposed_reset(self):
        return self._module.reset()


class Client(ClientBase):

    def send_command(self, msg):
        return self._service.exposed_send_command(msg)

    def read_reply(self, length=200):
        return self._service.exposed_read_reply(length)

    def send_read(self, msg, length=200):
        return self._service.exposed_send_read(msg, length)

    def send_read_verify(self, msg, length=200):
        return self._service.exposed_send_read_verify(msg, length)

    def set_P(self, P):
        return self._service.exposed_set_P(P)

    def set_I(self, I):
        return self._service.exposed_set_I(I)

    def set_D(self, D):
        return self._service.exposed_set_D(D)

    def set_int_time(self, time):
        return self._service.exposed_set_int_time(time)

    def set_offset(self, offset):
        return self._service.exposed_set_offset(offset)

    def get_status(self):
        return self._service.exposed_get_status()

    def get_all_vals(self):
        return self._service.exposed_get_all_vals()

    def get_P(self):
        return self._service.exposed_get_P()

    def get_I(self):
        return self._service.exposed_get_I()

    def get_D(self):
        return self._service.exposed_get_D()

    def get_int_time(self):
        return self._service.exposed_get_int_time()

    def get_offset(self):
        return self._service.exposed_get_offset()

    def get_errorval(self):
        return self._service.exposed_get_errorval()

    def get_integrator(self):
        return self._service.exposed_get_integrator()

    def get_PID_output(self):
        return self._service.exposed_get_PID_output()

    def reset(self):
        return self._service.exposed_reset()
