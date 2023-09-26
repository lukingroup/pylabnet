import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from mcculw import ul
from mcculw.enums import ULRange, InterfaceType, DigitalIODirection, DigitalPortType, ScanOptions
from mcculw.ul import ULError

MAX_OUTPUT = 10.0
RESOLUTION = 16 #bits


class Driver:
    """Driver for Measurement Computing USB-1608GX AO/DIO device.
    Make sure InstaCal is installed to access the device.
    """

    def __init__(self, device_id, board_number, logger=None, dummy=False):
        """Instantiate USB-1608GX board

        :device_id: (str) S/N of specific USB-1608GX board
        :board_number: (str) chosen board number used to identify this board
        """

        # Device name
        self.d_id = device_id
        self.bn = int(board_number)

        # Log
        self.log = LogHandler(logger=logger)

        # ignore_instacal() is used as recommended in mcculw examples. It prevents conflicts
        # with previous setting of DAQ parameters by InstaCal. Reminder that InstaCal MUST be
        # installed in order to detect the DAQ device. From mcculw documentation:
        # ignore_instacal():
        # Prevents the Universal Library from automatically adding a DAQ device that has been stored
        # in the cb.cfg file by InstaCal. This function must be the first Universal Library function
        # invoked in the application. Devices can then be added and configured at runtime using the
        # device discovery features.
        ul.ignore_instacal()

        devices = ul.get_daq_device_inventory(InterfaceType.ANY)
        if not devices:
            self.log.error('Error: No MCC USB DAQ devices found')

        self.log.info('Found ' + str(len(devices)) + ' DAQ device(s):')

        found_device = False

        for device in devices:
            if (device.product_name == "USB-1608GX") and (device.unique_id == self.d_id):
                self.log.info('  ' + str(device.product_name) + ' (' + str(device.unique_id) + ') - ' +
                              'Device ID = ' + str(device.product_id) + ' -- Match!')

                self.device = device
                found_device = True

            else:
                self.log.info('  ' + str(device.product_name) + ' (' + str(device.unique_id) + ') - ' +
                              'Device ID = ' + str(device.product_id))

        if found_device:
            ul.create_daq_device(self.bn, self.device)
            self.log.info('MCC USB-1608GX, device ID: ' + str(self.d_id) + ' set with board number ' + str(self.bn))

        else:
            self.log.error('Error: No MCC USB-1608GX devices with device ID ' + str(self.d_id) + ' found.')

        ul.d_config_port(self.bn, DigitalPortType.AUXPORT, DigitalIODirection.OUT)

    #analog input
    def get_ai_voltage(self, ai_channel, range=1):
        """Get analog input

        :ao_channel: (int) Input channel (0-7) 8 SE or 16 DIFF
        :voltage: (float) voltage value from -10 V to 10 V
        :range: (int) 1 (-10 to +10 V) , 0 (-5 to +5 V), 4 (-1 to +1 V), or 14 (-2 to +2 V)
        """
        #the a_in function returns the base 10 conversion of the binary value read
        raw_value = ul.a_in(self.bn, ai_channel, ULRange(range))

        #so we need to convert it to more useful units
        value_volts = ul.to_eng_units(self.bn, ULRange(range), raw_value)

        self.log.info(f'Read raw value of {raw_value} or {value_volts} V from channel {ai_channel}')

        return value_volts
