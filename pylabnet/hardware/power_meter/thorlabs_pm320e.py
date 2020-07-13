from pyvisa import VisaIOError, ResourceManager
import re
import numpy as np

from pylabnet.utils.logging.logger import LogHandler

class Driver:

    def __init__(self, gpib_address, logger):
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
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

        # We set a more forgiving timeout of 10s (default: 2s).
        self.device.timeout = 10000

    def get_power(self, channel):
        """ Returns the current power in watts on a desired channel

        :param channel: (int) channel to read power of (either 1 or 2)
        :return: (float) power in watts
        """

        power = self.device.query(f':POW[{channel}]:VAL?')
        return float(power)