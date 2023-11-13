from pyvisa import VisaIOError, ResourceManager
import numpy as np
import ctypes
from pylabnet.utils.logging.logger import LogHandler


class Driver:

    def __init__(self, device_key=None, logger=None):
        """Instantiate the driver for Newport power meter functionality. The USB hardware
        interfacing is outsourced to the NewportUSB class.

        NOTE: The device will be invisible cannot be connected to if there is another
        instance of Python already connected to it. Make sure to kill any existing
        connecting instances if the device somehow appears missing.

        :device_key: Device key of the unit, e.g. '2936-R SN8139'.
                    Can be found from the TestUsb.exe file under the Newport USB driver.
        :logger: An instance of a LogClient.
        """

        # Instantiate logger
        self.log = LogHandler(logger=logger)
        self.device_key = device_key

        try:
            # Instantiate USB device driver
            self.USBHandler = NewportUSB(self.log, self.device_key)

            # Check that we can talk to it
            query_result = self.query('*IDN?')
            self.log.info(f"Query result {str(query_result, encoding='utf-8')}.")
            self.log.info(f"Successfully connected to {device_key}.")

            # Set power units
            self.set_unit(1, "W")
            self.set_unit(2, "W")
            self.log.info(f"Set units to Watts.")
        except VisaIOError:
            self.log.error(f"Connection to {device_key} failed.")

    def write(self, command):
        """ Write a message to our default device.

        :command: (str) Command to be sent to device.
        :return: (int) operation error flag, 0 for no error
        """
        return self.USBHandler.write(command)

    def read(self, max_read_length=128):
        """ Read a message from our default device.

        :max_read_length: (int) Maximum length of message to be read
        :return: (str) Message read from device.
        """
        # The read from USBHandler gives extra info about bytes read and error flag, here we chop them off.
        return self.USBHandler.read(max_read_length)[0]

    def query(self, command, max_read_length=128):
        """ Write to, and immediately read from our default device.

        :command: (str) Command to be sent to device.
        :max_read_length: (int) Maximum length of message to be read.
        :return: (str) Message read from device.
        """
        self.write(command)
        return self.read(max_read_length)

    def set_channel(self, ch):
        """ Sets a given channel as active for all subsequent commands.
        :ch: (int) channel to set as active channel (either 1 or 2)
        :return: (int) operation error flag, 0 for no error
        """
        if ch not in [1, 2]:
            self.log.error("Channel must be either 1 or 2!")
            return 1
        return self.write(f"PM:CHANNEL {ch}")

    def get_channel(self):
        """ Get the current active channel.
        :return: (int) current active channel
        """
        return int(self.query(f"PM:CHANNEL?"))

    def get_power(self, ch):
        """ Returns the power in current units on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (float) power in the current units
        """
        if ch is not None:
            self.set_channel(ch)
        power = self.query(f"PM:POWER?")
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
            return self.write(f"PM:UNITS {unit}")
        else:
            self.log.error(f"Invalid units {unit_str} chosen, please choose from {units_dict.keys()}")
            return 1

    def get_unit(self, ch):
        """ Returns the current power unit on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (str) current unit of power
        """
        unit = int(self.query(f"PM:UNITS?"))
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
        wavelength = self.query(f'PM:LAMBDA?')
        return float(wavelength)

    def set_wavelength(self, ch, wavelength):
        """ Sets the wavelength on the active channel for responsivity calibration.
        :ch: (int) channel to access (either 1 or 2)
        :wavelength: (float) desired wavelength (nm) setting
        :return: (int) operation error flag, 0 for no error
        """
        if ch is not None:
            self.set_channel(ch)
        return self.write(f'PM:LAMBDA {wavelength}')

    def get_auto(self, ch):
        """ Returns the current auto power-range setting on the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (int) 1 for auto, 0 for manual mode
        """
        if ch is not None:
            self.set_channel(ch)
        auto = self.query(f'PM:AUTO?')
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
        return self.write(f'PM:AUTO {auto}')

    def get_range(self, ch):
        """ Returns the current power range for the active channel
        :ch: (int) channel to access (either 1 or 2)
        :return: (int) number from 0-7 indicating range. For our current sensor at 737nm,
        these correspond to 269 nW x 10**n.
        """
        if ch is not None:
            self.set_channel(ch)
        pr = self.query(f'PM:RANGE?')
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
        return self.write(f'PM:RANGE {p_range}')


class NewportUSB():

    def __init__(self, logger, device_key=None):
        """Interfaces with the USB DLL file to scan for accesible Newport USB devices, as well as
        reading and writing to these devcices. A particular device can be specified as the default
        so that we don't need to keep repeating the device key in all function calls.

        :logger: An instance of a LogClient.
        :device_key: Device key of the unit, e.g. '2936-R SN8139'.
                    Can be found from the TestUsb.exe file under the Newport USB driver.
                    If not specified, commands to read/write will need manual specification of device.
        """

        self.log = logger

        # Import DLL file necessary for communicating with device over USB
        self.dll = ctypes.windll.LoadLibrary('usbdll.dll')

        # Define type signatures for functions -- not strictly necessary but will help catch errors
        # Full type signatures and function headers are in NewpDll.h
        self.dll.newp_usb_open_devices.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.POINTER(ctypes.c_int)]
        self.dll.newp_usb_open_devices.retype = ctypes.c_long

        self.dll.newp_usb_get_model_serial_keys.argtypes = [ctypes.POINTER(ctypes.c_char_p)]
        self.dll.newp_usb_get_model_serial_keys.restype = ctypes.c_long

        self.dll.newp_usb_write_by_key.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong]
        self.dll.newp_usb_write_by_key.retype = ctypes.c_long

        self.dll.newp_usb_read_by_key.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        self.dll.newp_usb_read_by_key.retype = ctypes.c_long

        # Check how many devices are connected
        n_devices_C = ctypes.c_int()
        # 0 means scan all products, False means DeviceKey is used as the key to refer to devices
        err_flag = self.dll.newp_usb_open_devices(0, False, ctypes.byref(n_devices_C))

        if err_flag:
            self.log.eror("Failed to scan for open devices!")
            raise VisaIOError

        self.n_devices = n_devices_C.value
        self.log.info(f"Newport USB scan found {self.n_devices} devices.")
        print((f"Newport USB scan found {self.n_devices} devices."))

        # Read device keys from all found devices, start by initializing empty strings for the return values
        key_arr = (ctypes.c_char_p * self.n_devices)()
        for i in range(self.n_devices):
            key_arr[i] = b""
        err_flag = self.dll.newp_usb_get_model_serial_keys(key_arr)

        if err_flag:
            self.log.eror("Failed to scan for device keys!")
            raise VisaIOError

        # Convert received bytestrings into str, we now have a list of all connected devices
        self.device_keys = [str(s, encoding="utf-8") for s in key_arr]
        self.log.info(f"Newport USB scans found device keys: {str(self.device_keys)}.")
        print(f"Newport USB scans found device keys: {str(self.device_keys)}.")

        # Set the desired one as default
        self.set_device(device_key)

    def set_device(self, device_key):
        """ Set a given device as default so that all communuications are directed at that
        device unless specified otherwise.

        :device_key: (str) Device key of the desired default device.
        """

        if device_key is not None and device_key not in self.device_keys:
            self.log.error("Tried to set device to device that is not connected!")
            raise VisaIOError
        self.device_key = device_key
        self.log.info(f"Default Newport USB device is set to {device_key}.")

    def write_arb_device(self, device_key, command):
        """ Send a command to an arbitrary device specified by a device key.

        :device_key: (str) Device key of target device.
        :command: (str) Command to be sent to device.
        :return: (int) Operation error flag, 0 indicates no error.
        """

        if self.device_key is None:
            self.log.error("Default device key not set!")
            raise VisaIOError

        err_flag = self.dll.newp_usb_write_by_key(bytes(device_key, encoding="utf-8"),
                                                  bytes(command, encoding="utf-8"),
                                                  len(command))

        if err_flag:
            self.log.error(f"Error while writing command {command} to device {device_key}!")

        return err_flag

    def write(self, command):
        """ Send a command to our default device.

        :command: (str) Command to be sent to device.
        :return: (int) Operation error flag, 0 indicates no error.
        """

        return self.write_arb_device(self.device_key, command)

    def read_arb_device(self, device_key, max_read_length=128):
        """ Read a message from arbitrary device specified by a device key.

        :device_key: (str) Device key of target device.
        :max_read_length: (int) Maximum length of message to be read.
        :return: (str, int, int) Read message, bytes read, operation error flag, 0 indicates no error.
        """

        if self.device_key is None:
            self.log.error("Default device key not set!")
            raise VisaIOError

        buffer = ctypes.create_string_buffer(max_read_length)
        bytes_read = ctypes.c_ulong()

        err_flag = self.dll.newp_usb_read_by_key(bytes(device_key, encoding="utf-8"),
                                                 buffer,
                                                 max_read_length,
                                                 ctypes.byref(bytes_read))

        if err_flag:
            self.log.error(f"Error while reading from device {device_key}!")
            return 0, 0, 1

        if bytes_read == max_read_length:
            self.log.warn("Read length is equal to buffer length -- possibly need a larger buffer.")

        return buffer.value, bytes_read.value, err_flag

    def read(self, max_read_length=128):
        """ Read a message from our default device.

        :max_read_length: (int) Maximum length of message to be read.
        :return: (str, int, int) Read message, bytes read, operation error flag, 0 indicates no error.
        """

        return self.read_arb_device(self.device_key, max_read_length)
