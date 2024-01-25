from pyvisa import VisaIOError, ResourceManager
import numpy as np
from pylabnet.utils.logging.logger import LogHandler

import dacapi


class Driver:

    def __init__(self, serial_number, channels, logger=None):
        """Instantiate the driver for the Photon Spot bias box functionality.

        :serial_number: Serial number of the unit, e.g. 'PS2023010401'.
        :logger: An instance of a LogClient.
        """

        # Instantiate logger
        self.log = LogHandler(logger=logger)
        self.serial_number = serial_number
        self.ramp_step = 1.0
        self.channels = channels

        try:
            # Instantiate DAC interface
            self.dac = dacapi.DAC(simulate=False)
            urllist, seriallist = dacapi.find_devices()
            if serial_number not in seriallist:
                self.log.error(f"Serial number {serial_number} not in the list of devices found! {seriallist}")
            self.dac.connect(urllist=urllist, serial_number=serial_number)

            for ch in self.channels:
                self.set_bias(ch, ch["bias_current"])
                self.log.info(f"Set bias current {ch['bias_current']} uA for channel {ch}.")

        except Exception as e:
            self.log.error(e)

    def delatch(self, ch):
        """ Delatches the specified channel.
        :ch: (str) Channel name (e.g. "1A")
        """
        self.dac.delatch(channel=ch, step=self.ramp_step)

    def set_zero(self, ch):
        """ Sets the specified channel to zero bias.
        :ch: (str) Channel name (e.g. "1A")
        """
        self.dac.set_bias(channel=ch, biascurrent=0.0)

    def set_bias(self, ch, bias_current):
        """ Sets the bias current of the specified channel.
        :ch: (str) Channel name (e.g. "1A")
        :bias_current: (float) Bias current in uA
        """
        self.dac.set_bias(channel=ch, biascurrent=bias_current)

    def ramp_up(self, ch):
        """ Ramps the specified channel from zero to target bias.
        :ch: (str) Channel name (e.g. "1A")
        """
        self.dac.ramp_up(channel=ch, start=0.0, stop=self.bias_current, step=self.ramp_step)
