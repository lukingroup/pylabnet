import ctypes

from pylabnet.hardware.interface.wavemeter import WavemeterInterface, WavemeterError
from pylabnet.utils.logging.logger import LogHandler


class Driver(WavemeterInterface):
    """ Hardware class to control High Finesse Wavemeter."""

    def __init__(self, logger=None):
        """ Instantiate wavemeter

        :param logger: instance of LogClient class (optional)
        """

        # Log
        self.log = LogHandler(logger=logger)

        # Load WLM DLL
        try:
            self._wavemeterdll = ctypes.windll.LoadLibrary('wlmData.dll')

        except:
            msg_str = 'High-Finesse WS7 Wavemeter is not properly installed on this computer'
            self.log.error(msg_str)
            raise WavemeterError(msg_str)

        # Set all DLL function parameters and return value types
        self._wavemeterdll.GetWLMVersion.restype = ctypes.c_long
        self._wavemeterdll.GetWLMVersion.argtype = ctypes.c_long

        self._wavemeterdll.GetWLMCount.restype = ctypes.c_long
        self._wavemeterdll.GetWLMCount.argtype = ctypes.c_long

        self._wavemeterdll.GetWavelengthNum.restype = ctypes.c_double
        self._wavemeterdll.GetWavelengthNum.argtypes = [ctypes.c_long, ctypes.c_double]

        self._wavemeterdll.GetFrequencyNum.restype = ctypes.c_double
        self._wavemeterdll.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]

        # Check that WLM is running and log details
        self._is_running = self._wavemeterdll.GetWLMCount(0)
        if self._is_running > 0:
            self._wlm_version = self._wavemeterdll.GetWLMVersion(0)
            self.log.info(
                'Connected to High-Finesse Wavemeter WS-{0}'.format(self._wlm_version)
            )

        else:
            msg_str = 'High-Finesse WS7 Wavemeter software not running.\n'
            'Please run the Wavemeter software and try again.'
            self.log.warn(msg_str)
            # raise WavemeterError(msg_str)

    def get_wavelength(self, channel=1, units='Frequency (THz)'):
        """ Returns the wavelength in specified units for a given channel

        :param channel: Channel number from 1-8
        :param units: "Frequency (THz)" or "Wavelength (nm)". Defaults to frequency.
        """

        if units == 'Wavelength (nm)':
            return self._wavemeterdll.GetWavelengthNum(channel, 0)

        else:
            return self._wavemeterdll.GetFrequencyNum(channel, 0)
