import abc


class WavemeterInterface(abc.ABC):

    @abc.abstractmethod
    def get_wavelength(self, channel=1, units="Frequency (THz)"):
        pass


class WavemeterError(Exception):
    pass
