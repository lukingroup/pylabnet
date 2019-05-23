from interface.simple_pulse_generator import SimplePGenInterface
from hardware.ni_hsdio.ni_654x import NI654x
import rpyc
from core.service_base import ServiceBase
from core.client_base import ClientBase


class NI654xPGen(NI654x, SimplePGenInterface):
    def write(self, pb_obj):
        pass

    def cfg_rep(self, rep_numb):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_status(self):
        pass


class NI654xPGenService(ServiceBase):
    def exposed_write(self, pb_obj):
        pass

    def exposed_cfg_rep(self, rep_numb):
        pass

    def exposed_start(self):
        pass

    def exposed_stop(self):
        pass

    def exposed_get_status(self):
        pass


class NI654xPGenClient(ClientBase, SimplePGenInterface):

    def write(self, pb_obj):
        pass

    def cfg_rep(self, rep_numb):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_status(self):
        pass

