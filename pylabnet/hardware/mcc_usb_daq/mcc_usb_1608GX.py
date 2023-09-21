import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from mcculw import ul
from mcculw.enums import ULRange, InterfaceType, DigitalIODirection, DigitalPortType
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
    def get_ai_voltage(self, ao_channel, range):
        """Get analog input

        :ao_channel: (int) Input channel (0-7) 8 SE or 16 DIFF
        :voltage: (float) voltage value from -10 V to 10 V
        :range: (int) 1 (BIP10VOLTS) , 0 (BIP5VOLTS), 4 (BIP1VOLTS), or 14 (BIP2VOLTS)
        """
        return ul.a_in(self.bn, ao_channel, range)

    def ai_scan(self, low_ch, high_ch, num_samples, sample_rate, range, options):
        """Scans a range of A/D channels and stores the samples in an array

        :low_ch: (int) the first A/D channel in the scan
        :high_ch: (int) the last A/D channel in the scan (0-15 for SE, 0-7 for DIFF)
        :num_samples: (int) The total number of A/D samples to collect.
                            If more than one channel is being sampled,
                            the number of samples collected per channel is equal to
                            count / (high_ch – low_ch + 1).
        :sample_rate: (int) samples per second per channel, up to 500kS/second
                        For example, sampling four channels, 0 to 3, at a rate of 10,000 scans per second (10 kHz)
                        results in an A/D converter rate of 40 kHz: four channels at 10,000 samples per channel per second.
                        The actual sampling rate in some cases will vary a small amount from the requested rate.
                        The actual rate is returned.
        :range: (int) 1 (BIP10VOLTS) , 0 (BIP5VOLTS), 4 (BIP1VOLTS), or 14 (BIP2VOLTS)
        :options: (int) from ScanOptions in mcculw.enums
        """
        handle = ul.win_buf_alloc(num_samples)
        return ul.a_in_scan(self.bn, low_ch, high_ch, num_samples, sample_rate, range, handle, options)

    def set_dio(self, digital_pin, value):
        """Set digital output pin high (5 V) or low (0 V)

        :digital_pin: (int) Output pin (0-7)
        :value: (int) output value (0 or 1)
        """

        ul.d_bit_out(self.bn, DigitalPortType.AUXPORT, digital_pin, value)

    def set_trigger(self, type, patt_val, mask):
        """Selects the trigger source and sets up its params. Initiates a scan

        :type: (int) TrigType enum. This device does digital triggering and allows
                    TRIG_POS_EDGE, TRIG_NEG_EDGE, TRIG_HIGH, TRIG_LOW
        :patt_val: (int) sets the pattern value
        :mask: (int) selects the port mask
        """

        ul.set_trigger(self.bn, type, patt_val, mask)
