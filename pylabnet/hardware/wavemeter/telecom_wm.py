import pyvisa

from pylabnet.hardware.interface.wavemeter import WavemeterInterface, WavemeterError
from pylabnet.utils.logging.logger import LogHandler


class Driver(WavemeterInterface):
    """ Hardware class to control WA1650 Wavemeter."""

    def __init__(self, gpib_addr, logger=None):
        """ Instantiate wavemeter
        :param logger: instance of LogClient class (optional)
        """
        self.rm = pyvisa.ResourceManager()
        self.res_options = [10, 1, .1, .01, .001, .0001] #resolution options, in nm

        # Log
        self.log = LogHandler(logger=logger)

        # create connection
        try:
            self.device = self.rm.open_resource(gpib_addr)
            device_id = self.device.query('*IDN?')
            self.log.info(f'Connected to {device_id.strip()} on GPIB Address {gpib_addr.strip()}.')
        except pyvisa.VisaIOError:
            self.log.error(f'Connection to {gpib_addr} failed.')

        # Check that WLM is running and log details
        power = self.device.query(':MEASure:POWer?').strip()
        pwrunit = self.device.query(':DISP:UNIT:POWer?').strip()
        resolution = self.device.query('DISP:RESolution?').strip()

        if power > 0:
            self._is_running = 1
            self.log.info(f'Connected to WA1650. Measuring {power} {pwrunit}. Resolution is set to {resolution} nm, max is 0.0001 nm.')
        else:
            msg_str = 'WA1650 does not register laser power.\n'
            'Please check the optical connection and try again.'
            self.log.warn(msg_str)
            # raise WavemeterError(msg_str)

        resolution = self.device.write(':DISPlay:RESolution .0001') # why would anyone want less than MAX RES :p

        self.log.info('Device initialized with resolution = 0.0001')


    def get_wavelength(self, channel=1, units='Frequency (THz)'):
        """ Returns the wavelength in specified units for a given channel
        :param channel: Channel number from 1-8
        :param units: "Frequency (THz)" or "Wavelength (nm)". Defaults to frequency.
        """

        if units == 'Wavelength (nm)':
            return float(self.device.query(':MEASure:WAVelength?').strip()) # already in nm

        else:
            freq_ghz = self.device.query(':MEASure:FREQuency?').strip() # in GHz
            freq_thz = float(freq_ghz)/1000 # convert to THz
            return freq_thz


# """FUTURE; WOULD REQUIRE WAVEMETER CLASS MODS?"""
#     """def set_resolution(res):
#         if res in self.res_options:
#             self.device.write(f':DISPlay:RESolution {res}')
#             self.log.info(f'Resolution set to {res}')
#             return
#         else:
#             self.log.error('Resolution must be one of' + self.res_options)
#             return