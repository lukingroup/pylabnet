from pyvisa import VisaIOError, ResourceManager
import re
import numpy as np

from pylabnet.utils.logging.logger import LogHandler




class Driver():

    def reset(self):
        """ Create factory reset"""
        self.device.write('*RST')
        self.log.info("Reset to factory settings successfull.")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class.

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient.
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

        # Reset to factory settings.
        self.reset()

    def output_on(self):
        """ Turn output on."""

        res = self.device.write('OUTPut ON')

    def output_off(self):
        """ Turn output off."""

        res = self.device.write('OUTP OFF')

    def set_frequency(self, freq):
        """ Set frequency (in Hz)
        
        :freq: Target frequency in Hz
        """

        if not 10e6 < freq < 20e9:
            self.log.error("Frequency must be between 10 MHz and 20 GHz")
        res = self.device.write(f'freq {freq}')
        return res


    def set_power(self, power):
        """ Set output power (in dBm)
        
        :power: Target pwoer in dBm
        """

        if  power > 26:
            self.log.error("Power must be smaller then 26dBm")
        res = self.device.write(f'pow {power}')
        return res


    