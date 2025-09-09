from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    """RPC Service exposing BKtel amplifier commands."""

    def exposed_read_ra(self):
        return self._module.read_ra()

    def exposed_read_rmode(self):
        return self._module.read_rmode()

    def exposed_read_rpc(self):
        return self._module.read_rpc()

    def exposed_set_spc(self, value):
        return self._module.set_spc(value)

    def exposed_smode_off(self):
        return self._module.smode_off()

    def exposed_smode_pc(self):
        return self._module.smode_pc()

    def exposed_close(self):
        """No-op close: keeps the serial port open on the server."""
        return self._module.close()

    def exposed_force_close(self):
        """Forcefully close the serial port on the server (use sparingly)."""
        return self._module.force_close()


class Client(ClientBase):
    """Client-side convenience API mirroring the service methods."""

    def read_ra(self):
        return self._service.exposed_read_ra()

    def read_rmode(self):
        return self._service.exposed_read_rmode()

    def read_rpc(self):
        return self._service.exposed_read_rpc()

    def set_spc(self, value):
        return self._service.exposed_set_spc(value)

    def smode_off(self):
        return self._service.exposed_smode_off()

    def smode_pc(self):
        return self._service.exposed_smode_pc()

    def close(self):
        """No-op on the server (keeps port open)."""
        return self._service.exposed_close()

    def force_close(self):
        """Forcefully close the serial port on the server."""
        return self._service.exposed_force_close()
