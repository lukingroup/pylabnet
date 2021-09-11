from pyvisa import VisaIOError, ResourceManager
import numpy as np

from pylabnet.utils.logging.logger import LogHandler


class Driver:

    def __init__(self, gpib_address=None, logger=None):
        """Instantiate driver class.

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: An instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id}.")
            # We set a more forgiving timeout of 10s (default: 2s).
            # self.device.timeout = 10000
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

    def get_power(self, channel):
        """ Returns the current power in watts on a desired channel

        :param channel: (int) channel to read power of (either 1 or 2)
        :return: (float) power in watts
        """

        power = self.device.query(f':POW{channel}:VAL?')
        return float(power)

    def get_wavelength(self, channel):
        """ Returns the current wavelength in nm for the desired channel

        :param channel: (int) channel to read wavelength of
        :return: (int) wavelength
        """

        wavelength = self.device.query(f':WAVEL{channel}:VAL?')
        return int(float(wavelength))

    def get_range(self, channel):
        """ Returns the current power range for the channel

        :param channel: (int) channel to read range of
        :return: (str) range
        """

        pr = self.device.query(f':PRANGE{channel}?')
        return pr

    def set_wavelength(self, channel, wavelength):
        """ Sets the wavelength

        :param channel: (int) channel to set wavelength of
        """

        self.device.write(f':WAVEL{channel}:VAL {wavelength}')

    def set_range(self, channel, p_range):
        """ Sets the range

        :param channel: (int) channel to set range of
        :param p_range: (str) range string identifier, can be anything in
            'AUTO', 'R1NW', 'R10NW', 'R100NW', 'R1UW', 'R10UW', 'R100UW', 'R1MW',
            'R10MW', 'R100MW', 'R1W', 'R10W', 'R100W', 'R1KW'
        """

        self.device.write(f':PRANGE{channel} {p_range}')
