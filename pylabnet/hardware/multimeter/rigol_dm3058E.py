from pyvisa import VisaIOError, ResourceManager

from pylabnet.utils.logging.logger import LogHandler, LogClient
import numpy as np
import time


class Driver():
    """Driver class for GPIB controlled Agilent EE405 Spectrum analyser"""

    def reset(self):
        """ Create factory reset"""
        self.device.write('*RST')
        self.log.info("Reset to factory settings successfull.")

    def set_resistance_measurement(self):
        self.device.write(":FUNCtion:RESistance")

    def set_resistance_range(self, res_range):
        """ Setting resistance measurment range
        
        0: 200 Ohm
        1: 2 kOhm
        2: 20 kOhhm
        3: 200 kOhm
        4: 1MOhm
        5: 10 MOhm
        6: 100 MOhm
        """

        setting_dict = {
            0 : "200 Ohm",
            1 : "2 kOhm",
            2 : "20 kOhm",
            3 : "200 kOhm",
            4 : "1 MOhm",
            5 : "10 MOhm",
            6 : "100 MOhm"
        }

        self.device.write(f":MEASure:RESistance {res_range}")
        self.log.info(f"Successfully set resistance range to {setting_dict[res_range]}.")


    def get_resistance(self):
        """ Return measured resistance"""
        return self.device.query(":MEASure:RESistance?")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class

        :gpib_address: GPIB-address of multimeter, e.g. 'USB0::0x1AB1::0x09C4::DM3R242902020::INSTR'
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
            self.device.write_termination = '\n'
            self.device.read_termination = '\n'
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

        # reset to factory settings
        self.reset()


if __name__ == "__main__":

    # Instantiate
    logger = LogClient(
        host='192.168.50.111',
        port=38967,
    module_tag='Rigol MM'
    )


    gpib_address = 'USB0::0x1AB1::0x09C4::DM3R242902020::INSTR'
    mm = Driver(gpib_address = gpib_address, logger = logger)

    mm.set_resistance_measurement()
    time.sleep(1)
    mm.set_resistance_range(0)
    time.sleep(1)
    mm.get_resistance()