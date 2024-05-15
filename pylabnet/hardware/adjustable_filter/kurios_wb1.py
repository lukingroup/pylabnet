from pyvisa import VisaIOError, ResourceManager
import numpy as np
from pylabnet.utils.logging.logger import LogHandler


class Driver:

    def __init__(self, device_addr=None, logger=None):
        """Instantiate the driver for Kurios WB-1 functionality.

        :device_addr: USB address of the unit, e.g. 'ASRL7::INSTR'.
        :logger: An instance of a LogClient.
        """

        # Instantiate logger
        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()
        self.device_addr = device_addr

        try:
            # Instantiate Serial resource
            self.device = self.rm.open_resource(self.device_addr, baud_rate=115200, write_termination="\r", read_termination="\r>", query_delay=0.25)

            # Check that we can talk to it
            query_result = self.device.query('*IDN?')
            self.log.info(f"Query result {query_result}.")
            self.log.info(f"Successfully connected to {device_addr}.")

        except VisaIOError:
            self.log.error(f"Connection to {device_addr} failed.")

    def get_wavelength(self):
        """ Returns the current passband wavelength.
        :return: (int) Current passband wavelength in nm
        """
        # Return string is in the form "WL=420.000"
        wavelength_str = ""
        while wavelength_str == "":
            wavelength_str = self.device.query('WL?')

        wavelength = int(float(wavelength_str.split("=")[1]))
        return wavelength

    def set_wavelength(self, wavelength):
        """ Sets the current passband wavelength.
        :wavelength: (int) desired wavelength (nm) setting
        """
        # Float to convert from str to float, then cast to int
        self.device.write(f'WL={int(wavelength)}')

    def get_range(self):
        """ Returns the current power range for the active channel
        :return: (2-tuple ints) min and max wavelength of filter range
        """
        # Return string is in the form "WLmax=730.000\rWLmin=420.000"
        range_str = ""
        while range_str == "":
            range_str = self.device.query(f'SP?')

        max_str, min_str = range_str.split("\r")
        wl_max = int(float(max_str.split("=")[1]))
        wl_min = int(float(min_str.split("=")[1]))
        return (wl_min, wl_max)

    def get_output(self):
        """ Returns the filter operating mode.
        :return: (int) 0 = OFF, 1 = ON
        """
        # Our filter only has BLACK (1) and WIDE (2) modes.
        bw_str = ""
        while bw_str == "":
            bw_str = self.device.query('BW?')

        bw = int(bw_str.split("=")[1])
        # Convert from (1/2) to (0/1)
        return int(bw == 2)

    def set_output(self, output):
        """ Sets the filter operating mode.
        :output: (int)  0 = OFF, 1 = ON
        """
        if output not in (0, 1):
            self.log.warn(f"Operating mode must be 0 or 1.")
            return

        # Our filter only has BLACK (1) and WIDE (2) modes.
        # Convert from (0/1) to (1/2)
        bw = output + 1
        self.device.write(f'BW={bw}')
