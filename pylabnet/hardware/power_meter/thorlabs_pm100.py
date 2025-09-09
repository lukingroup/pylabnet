from pyvisa import VisaIOError, ResourceManager
import numpy as np
from ThorlabsPM100 import ThorlabsPM100

from pylabnet.utils.logging.logger import LogHandler


class Driver:

    def __init__(self, gpib_address=None, logger=None):
        """Instantiate driver class.

        :gpib_address: GPIB/USB-address of the scope, e.g. 'USB0::0x1313::0x8075::P5003743::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: An instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            inst = self.rm.open_resource(gpib_address)
            self.device = ThorlabsPM100(inst=inst)
            # self.device = self.rm.open_resource(gpib_address)
            # device_id = self.device.query('*IDN?')
            # self.log.info(f"Successfully connected to {device_id}.")
            # We set a more forgiving timeout of 10s (default: 2s).
            # self.device.timeout = 10000
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

    def get_power(self):
        """ Returns the current power in watts

        :return: (float) power in watts
        """

        power = self.device.read
        return float(power)

    def get_wavelength(self):
        """ Returns the current wavelength in nm for the desired channel
        :return: (int) wavelength
        """

        wavelength = self.device.sense.correction.wavelength
        return int(float(wavelength))

    def get_range(self, channel):
        """ Returns the current power range
        :return: (str) range
        """
        pr = self.device.sense.power.dc.range.upper
        return pr

    def set_wavelength(self, wavelength):
        """ Sets the wavelength in nm

        """
        self.device.power_meter.sense.correction.wavelength = wavelength

    def set_range_auto(self):
        """ Sets the range to auto

        """

        self.device.sense.power.dc.range.auto = "ON"
