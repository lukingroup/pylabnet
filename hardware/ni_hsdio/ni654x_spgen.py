from interface.simple_pulse_generator import SimplePGenInterface
from hardware.ni_hsdio.ni654x import NI654x
from core.service_base import ServiceBase
from core.client_base import ClientBase
import pickle
import copy


class NI654xSPGen(NI654x, SimplePGenInterface):

    def __init__(self, dev_name_str, dll_path_str, logger=None):
        super().__init__(
            dev_name_str=dev_name_str,
            dll_path_str=dll_path_str,
            logger=logger
        )
        self.set_active_chs(chs_str='0-31')
        self.set_mode(mode_string='W')

    def write(self, pb_obj, step_adj=True):

        wfm_set = copy.deepcopy(self.writn_wfm_set)

        for wfm_name in wfm_set:
            self.del_wfm(wfm_name=wfm_name)

        return self.write_wfm(
            pb_obj=pb_obj,
            step_adj=step_adj
        )


class NI654xSPGenService(ServiceBase):
    def exposed_write(self, pb_obj_pckl, step_adj=True):

        pb_obj = pickle.loads(pb_obj_pckl)

        return self._module.write(
            pb_obj=pb_obj,
            step_adj=step_adj
        )

    def exposed_set_rep(self, rep_num):
        return self._module.set_rep(
            rep_num=rep_num
        )

    def exposed_start(self):
        return self._module.start()

    def exposed_stop(self):
        return self._module.stop()

    def exposed_get_status(self):
        return self._module.get_status()


class NI654xSPGenClient(ClientBase, SimplePGenInterface):

    def write(self, pb_obj, step_adj=True):

        pb_obj_pckl = pickle.dumps(pb_obj)

        return self._service.exposed_write(
            pb_obj_pckl=pb_obj_pckl,
            step_adj=step_adj
        )

    def set_rep(self, rep_num):
        return self._service.exposed_set_rep(
            rep_num=rep_num
        )

    def start(self):
        return self._service.exposed_start()

    def stop(self):
        return self._service.exposed_stop()

    def get_status(self):
        return self._service.exposed_get_status()

