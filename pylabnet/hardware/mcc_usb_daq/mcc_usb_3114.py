import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from mcculw import ul
from mcculw.enums import ULRange, InterfaceType, DigitalIODirection, DigitalPortType
from mcculw.ul import ULError

MAX_OUTPUT = 10


class Driver:
    """Driver for Measurement Computing USB-3114 AO/DIO device.
    Make sure InstaCal is installed to access the device.
    """

    def __init__(self, device_id, board_number, logger=None, dummy=False):
        """Instantiate USB-3114 board

        :device_id: (str) S/N of specific USB-3114 board
        :board_number: (str) chosen board number used to identify this board
        """

        # Device name
        self.d_id = device_id
        self.bn = int(board_number)

        # Log
        self.log = LogHandler(logger=logger)

        ul.ignore_instacal()
        devices = ul.get_daq_device_inventory(InterfaceType.ANY)
        if not devices:
            self.log.error('Error: No MCC USB DAQ devices found')

        self.log.info('Found ' + str(len(devices)) + ' DAQ device(s):')

        found_device = False

        for device in devices:
            if (device.product_name == "USB-3114") and (device.unique_id == self.d_id):
                self.log.info('  ' + str(device.product_name) + ' (' + str(device.unique_id) + ') - ' +
                              'Device ID = ' + str(device.product_id) + ' -- Match!')

                self.device = device
                found_device = True

            else:
                self.log.info('  ' + str(device.product_name) + ' (' + str(device.unique_id) + ') - ' +
                              'Device ID = ' + str(device.product_id))

        if found_device:
            ul.create_daq_device(self.bn, self.device)
            self.log.info('MCC USB-3114, device ID: ' + str(self.d_id) + ' set with board number ' + str(self.bn))

        else:
            self.log.error('Error: No MCC USB-3114 devices with device ID ' + str(self.d_id) + ' found.')

        ul.d_config_port(self.bn, DigitalPortType.AUXPORT, DigitalIODirection.OUT)

    # def set_ao_voltage(self, ao_channel, voltage):
    #     """Set analog output

    #     :ao_channel: (int) Output channel (0-15)
    #     :voltage: (float) voltage value from 10 V to voltage_max value
    #     """

    #     if voltage > MAX_OUTPUT:
    #         self.log.info("WARNING: Voltage set to " + str(voltage) + " V but max voltage set is 10 V.")

    #     output_int = np.min(1, voltage/MAX_OUTPUT) * (2 ** 16 - 1)

    #     ul.a_out(self.bn, ao_channel, ULRange(1), output_int)

    # def set_dio(self, digital_pin, value):
    #     """Set digital output pin high (5 V) or low (0 V)

    #     :digital_pin: (int) Output pin (0-7)
    #     :value: (int) output value (0 or 1)
    #     """

    #     ul.d_bit_out(self.bn, DigitalPortType.AUXPORT, digital_pin, value)
