from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.hardware.interface.wavemeter import WavemeterInterface


class Service(ServiceBase):

    def exposed_get_wavelength(self, channel, units):
        return self._module.get_wavelength(
            channel=channel,
            units=units
        )


class Client(ClientBase, WavemeterInterface):

    def get_wavelength(self, channel=1, units="Frequency(THz)"):
        return self._service.exposed_get_wavelength(channel, units)
