import numpy as np
import ctypes

from pylabnet.utils.logging.logger import LogHandler
from mcculw import ul
from mcculw.enums import (
    ULRange, InterfaceType, DigitalIODirection, DigitalPortType, ScanOptions, DigitalPortType)
from mcculw.ul import (
    ULError, win_buf_alloc_32, win_buf_free, win_buf_to_array_32)
from mcculw.device_info import DaqDeviceInfo

MAX_OUTPUT = 10.0


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

    def set_ao_voltage(self, ao_channel, voltage):
        """Set analog output

        :ao_channel: (int) Output channel (0-15)
        :voltage: (float) voltage value from 0 V to 10 V
        """

        if voltage > MAX_OUTPUT:
            self.log.info("WARNING: Voltage set to " + str(voltage) + " V but max voltage set is 10 V.")

        output_int = int(np.round(np.min([1, voltage / MAX_OUTPUT]) * (2 ** 16 - 1)))

        ul.a_out(self.bn, ao_channel, ULRange(1), output_int)

    def set_dio(self, digital_pin, value):
        """Set digital output pin high (5 V) or low (0 V)

        :digital_pin: (int) Output pin (0-7)
        :value: (int) output value (0 or 1)
        """

        ul.d_bit_out(self.bn, DigitalPortType.AUXPORT, digital_pin, value)

    def ramp_scan(self, center, width, num_points):
        """
        Returns a NumPy array of linearly spaced values centered around a given value.

        Parameters:
        - center (float): The center value of the array.
        - width (float): The total width of the range (from center - width/2 to center + width/2).
        - num_points (int): The number of points in the array.

        Returns:
        - numpy.ndarray: the ramp for the cavity scan.
        """
        start = center - width / 2
        end = center + width / 2
        return np.linspace(start, end, num_points)

    def ao_waveform_scan(self, ao_channels, waveforms, scan_rate, num_samples, digital_trigger_ports):
        assert len(ao_channels) == len(waveforms), "Each AO channel needs a waveform"

        num_channels = len(ao_channels)
        num_points = num_channels * num_samples

        # Pull info on the DAQ
        ao_info = DaqDeviceInfo(self.bn).get_ao_info()
        res = ao_info.resolution
        max_dac = 2**res - 1
        min_v, max_v = -10.0, 10.0

        def to_dac(wave):
            return ((wave - min_v) / (max_v - min_v) * max_dac).astype(np.uint16)

        dac_waveforms = [to_dac(w) for w in waveforms]

        # Check if channels are consecutive
        consecutive = (max(ao_channels) - min(ao_channels) + 1 == len(ao_channels))

        if consecutive:
            print("[INFO] Using hardware-times a_out_scan.")
            # Interleave the waveform data
            interleaved = np.empty(num_points, dtype=np.float32)
            for i in range(num_samples):
                for j in range(num_channels):
                    idx = i * num_channels + j
                    try:
                        interleaved[idx] = waveforms[j][i]
                    except IndexError:
                        interleaved[idx] = 0.0

            # Allocate buffer and copy data into it
            memhandle = win_buf_alloc_32(num_points)
            if memhandle == 0:
                raise RuntimeError("Failed to allocate output memory buffer.")

            # Copy the output array to memory buffer
            ctypes.memmove(memhandle, interleaved.ctypes.data, interleaved.nbytes)

            # Prepare Digital Trigger
            if digital_trigger_ports is not None:
                for dtp in digital_trigger_ports:
                    self.set_dio(dtp, 1) # Output

            ul.a_out_scan(
                self.bn,
                min(ao_channels),
                max(ao_channels),
                num_points,
                scan_rate,
                ULRange.BIP10VOLTS,
                memhandle,
                0
            )

        else:
            print("[WARN] Channels not consecutive: falling back to software-timed loop....")
            print("...you wish! I still have to figure that out. Fail.")
            #interval = 1 / scan_rate
            #for i in range(num_points):
            #    for ch, data in zip(ao_channels, dac_waveforms):
            #        ul.a_out(self.bn, ch, ULRange.BIP10VOLTS, data[i])

        # Turn off trigger
        if digital_trigger_ports is not None:
            for dtp in digital_trigger_ports:
                self.set_dio(dtp, 0)

        ul.win_buf_free(memhandle)
