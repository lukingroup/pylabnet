from pylabnet.hardware.interface.simple_p_gen import SimplePGenInterface
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase
import pickle

# TODO: add automatic frequency setting
# TODO: (analyze given PulseBlock, find smallest interval, set 1/10 sampling rate)


class NI654xSPGen(SimplePGenInterface):

    def __init__(self, ni654x_inst):
        self._dev = ni654x_inst

    def activate_interface(self):

        # TODO: add mutex check and lock (force lock option)

        # Reset device
        #   store hardware settings which are not controlled by logic,
        #   to restore them after reset()
        #   [logic does not know anything about this params, so it should not
        #   introduce any changes to them by calling activate_interface()].
        tmp_map_dict = self._dev.map_dict
        tmp_samp_rate = self._dev.get_samp_rate()
        #   full hardware reset
        self._dev.reset()

        # Restore hardware settings which are not controlled by logic
        # but were changed by self._dev.reset()
        self._dev.map_dict = tmp_map_dict
        self._dev.set_samp_rate(samp_rate=tmp_samp_rate)

        # Configure the device to operate as Simple Pulse Generator
        self._dev.set_mode(mode_string='W')
        self._dev.set_active_chs(chs_str='0-31')

        return 0

    def write(self, pb_obj, len_adj=True):

        self._dev.clr_mem()

        return self._dev.write_wfm(
            pb_obj=pb_obj,
            len_adj=len_adj
        )

    def set_rep(self, rep_num):
        return self._dev.set_rep(
            rep_num=rep_num
        )

    def start(self):
        return self._dev.start()

    def stop(self):
        return self._dev.stop()

    def get_status(self):
        """Get status of the device

        0 - 'Idle'
        1 - 'Running'
        Exception is produced in the case of any error
        (for example, connection to the device is lost)

        :return: (int) status code
                 Exception is produced in the case of error
        """

        return self._dev.get_status()


class NI654xSPGenService(ServiceBase):

    def exposed_activate_interface(self):
        return self._module.activate_interface()

    def exposed_write(self, pb_obj_pckl, len_adj=True):

        pb_obj = pickle.loads(pb_obj_pckl)

        return self._module.write(
            pb_obj=pb_obj,
            len_adj=len_adj
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

    def activate_interface(self):
        return self._service.exposed_activate_interface()

    def write(self, pb_obj, len_adj=True):

        pb_obj_pckl = pickle.dumps(pb_obj)

        return self._service.exposed_write(
            pb_obj_pckl=pb_obj_pckl,
            len_adj=len_adj
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
