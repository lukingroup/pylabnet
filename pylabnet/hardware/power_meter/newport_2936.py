from pyvisa import VisaIOError, ResourceManager
import numpy as np
from pylabnet.utils.logging.logger import LogHandler


class Driver:

    def __init__(self, device_addr=None, logger=None):
        """Instantiate the driver for Newport power meter functionality.

        NOTE: The device will be invisible cannot be connected to if there is another
        instance of Python already connected to it. Make sure to kill any existing
        connecting instances if the device somehow appears missing.

        :device_key: Device key of the unit, e.g. '2936-R SN8139'.
                    Can be found from the TestUsb.exe file under the Newport USB driver.
        :logger: An instance of a LogClient.
        """

        # Instantiate logger
        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()
        self.device_addr = device_addr

        try:
            # Instantiate Serial resource
            self.device = self.rm.open_resource(self.device_addr, baud_rate=38400, read_termination="\r\n")
            self.device.write("ECHO 0")

            # Check that we can talk to it
            query_result = self.device.query('*IDN?')
            self.log.info(f"Query result {query_result}.")
            self.log.info(f"Successfully connected to {device_addr}.")

            # Set power units
            self.set_unit(1, "W")
            self.set_unit(2, "W")
            self.log.info(f"Set units to Watts.")
        except VisaIOError:
            self.log.error(f"Connection to {device_addr} failed.")

    def set_channel(self, ch):
        """ Sets a given channel as active for all subsequent commands.
        :ch: (int) channel to set as active channel (either 1 or 2)
        :return: (int) operation error flag, 0 for no error
        """
        if ch not in [1, 2]:
            self.log.error("Channel must be either 1 or 2!")
            return 1
        return self.device.write(f"PM:CHANNEL {ch}")

    def get_channel(self):
        """ Get the current active channel.
        :return: (int) current active channel
        """
        return int(self.device.query(f"PM:CHANNEL?"))

    def get_power(self, ch):
        """ Returns the power in current units on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (float) power in the current units
        """
        if ch is not None:
            self.set_channel(ch)
        power = self.device.query(f"PM:POWER?")
        return float(power)

    def set_unit(self, ch, unit_str):
        """ Set the current power unit on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :unit: (str) unit of power to be set
        :return: (int) operation error flag, 0 for no error
        """
        units_dict = {"A": 0, "V": 1, "W": 2, "W/cm^2": 3, "J": 4, "J/cm^2": 5, "dBm": 6}
        if ch is not None:
            self.set_channel(ch)
        if unit_str in units_dict:
            unit = units_dict[unit_str]
            return self.device.write(f"PM:UNITS {unit}")
        else:
            self.log.error(f"Invalid units {unit_str} chosen, please choose from {units_dict.keys()}")
            return 1

    def get_unit(self, ch):
        """ Returns the current power unit on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (str) current unit of power
        """
        unit = int(self.device.query(f"PM:UNITS?"))
        units_dict = {0: "A", 1: "V", 2: "W", 3: "W/cm^2", 4: "J", 5: "J/cm^2", 6: "dBm", 11: "Sun"}
        if ch is not None:
            self.set_channel(ch)
        if unit in units_dict:
            return units_dict[unit]
        else:
            self.log.error(f"Invalid unit {unit} returned.")
            return None

    def get_wavelength(self, ch):
        """ Returns the current wavelength in nm on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (int) wavelength setting for responsivity purposes.
        """
        if ch is not None:
            self.set_channel(ch)
        wavelength = self.device.query(f'PM:LAMBDA?')
        return int(wavelength)

    def set_wavelength(self, ch, wavelength):
        """ Sets the wavelength on the active channel for responsivity calibration.
        :ch: (int) channel to access (either 1 or 2)
        :wavelength: (int) desired wavelength (nm) setting
        :return: (int) operation error flag, 0 for no error
        """
        if ch is not None:
            self.set_channel(ch)
        # Float to convert from str to float, then cast to int
        return self.device.write(f'PM:LAMBDA {int(float(wavelength))}')

    def get_auto(self, ch):
        """ Returns the current auto power-range setting on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (int) 1 for auto, 0 for manual mode
        """
        if ch is not None:
            self.set_channel(ch)
        auto = self.device.query(f'PM:AUTO?')
        return int(auto)

    def set_auto(self, ch, auto):
        """ Sets the current auto power-range setting on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :auto: (int) 1 for auto, 0 for manual mode
        :return: (int) operation error flag, 0 for no error
        """
        auto = int(auto) # Convert bools to ints
        if ch is not None:
            self.set_channel(ch)
        if auto not in [0, 1]:
            self.log.error(f"Auto should be either 0 or 1.")
            return 1
        return self.device.write(f'PM:AUTO {auto}')

    def get_range(self, ch):
        """ Returns the current power range for the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (int) number from 0-7 indicating range. For our current sensor at 737nm,
        these correspond to 269 nW x 10**n.
        """
        if ch is not None:
            self.set_channel(ch)
        pr = self.device.query(f'PM:RANGE?')
        return int(pr)

    def set_range(self, ch, p_range):
        """ Sets the power range for the active channel
        :ch: (int) channel to access (either 1 or 2)
        :p_range: (int) number from 0-7 indicating range. For our current sensor at 737nm,
        these correspond to 269 nW x 10**n.
        :return: (int) operation error flag, 0 for no error
        """
        if ch is not None:
            self.set_channel(ch)
        if p_range not in range(8):
            self.log.error(f"p_range should be an int from 0-7.")
            return 1
        return self.device.write(f'PM:RANGE {p_range}')
