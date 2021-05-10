from pyvisa import VisaIOError, ResourceManager

from pylabnet.utils.logging.logger import LogHandler
import numpy as np
import time


class Driver():
    """Driver class"""

    def reset(self):
        """ Create factory reset"""
        self.device.write('*RST')
        self.log.info("Reset to factory settings successfull.")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class

        :gpib_address: GPIB-address of spectrum analyzer, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient
        """

        # Instantiate log
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

        # reset to factory settings
        self.reset()

    def turn_laser_off(self):
        """ Power off display """
        self.device.write('OUTPut1:STATe 0') # temp control
        self.device.write('OUTPut2:STATe 0') # diode
        self.log.info("Laser off.")

    def turn_laser_on(self):
        """ Power on display """
        self.device.write('OUTPut2:STATe 1') # temp control
        self.device.write('OUTPut1:STATe 1') # diode
        self.log.info("Laser on.")

    def set_current(self, amps):
        """ Sets current setpoint in mA
        :amps:
        """

        if not 0 <= amps <= 60:
            self.log.error(
                f'Invalid current ({amps}mA). Attenuation must be between 0A and 60mA'
            )
        self.device.write(f'SOURce1:CURRent:LEVel:AMPLitude {amps*1e-3}')
        self.log.info(f'Current setpoint set to {amps}mA.')