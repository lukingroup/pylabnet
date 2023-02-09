
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
import pickle


class Service(ServiceBase):

    def exposed_activate_interface(self):
        return self._module.activate_interface()

    # Output control

    def exposed_on(self):
        return self._module.on()

    def exposed_off(self):
        return self._module.off()

    def exposed_get_status(self):
        return self._module.get_status()

    # Power

    def exposed_get_pwr(self):
        return self._module.get_pwr()

    def exposed_set_pwr(self, pwr):
        return self._module.set_pwr(pwr=pwr)

    # Frequency

    def exposed_get_freq(self):
        res = self._module.get_freq()
        return pickle.dumps(res)

    def exposed_set_freq(self, freq):
        return self._module.set_freq(freq=freq)

    def exposed_set_freq_swp(self, start, stop, n_pts):
        res = self._module.set_freq_swp(
            start=start,
            stop=stop,
            n_pts=n_pts
        )
        return pickle.dumps(res)

    def exposed_reset_swp_pos(self):
        return self._module.reset_swp_pos()

    def exposed_get_mode(self):
        return self._module.get_mode()


class Client(ClientBase):

    def activate_interface(self):
        return self._service.exposed_activate_interface()

    # Output control

    def on(self):
        return self._service.exposed_on()

    def off(self):
        return self._service.exposed_off()

    def get_status(self):
        return self._service.exposed_get_status()

    # Power

    def get_pwr(self):
        return self._service.exposed_get_pwr()

    def set_pwr(self, pwr):
        return self._service.exposed_set_pwr(
            pwr=float(pwr)
        )

    # Frequency

    def get_freq(self):
        ret_pckl = self._service.exposed_get_freq()
        return pickle.loads(ret_pckl)

    def set_freq(self, freq):
        return self._service.exposed_set_freq(
            freq=float(freq)
        )

    def set_freq_swp(self, start, stop, n_pts):
        res_pckl = self._service.exposed_set_freq_swp(
            start=start,
            stop=stop,
            n_pts=n_pts
        )

        return pickle.loads(res_pckl)

    def reset_swp_pos(self):
        return self._service.exposed_reset_swp_pos()

    def get_mode(self):
        return self._service.exposed_get_mode()
