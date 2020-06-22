""" Module for controlling Smaract open-loop nanopositioners using the MCS-2 controller """

import ctypes

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import value_to_bitval, bitval_to_value


class MCS2:

    # property keys and other constants
    PKEY_NUM_BUS = int("0x020F0016", 16)
    PKEY_NUM_CH = int('0x020F0017', 16)
    PKEY_NUM_BUS_CH = int('0x02030017', 16)
    PKEY_MOVE_MODE = int('0x03050087', 16)
    PKEY_STEP_FREQ = int('0x0305002E', 16)
    PKEY_STEP_AMP = int('0x03050030', 16)
    PKEY_VOLT = int('0x0305001F', 16)
    PKEY_DC_VEL = int('0x0305002A', 16)
    PKEY_CURRENT_STATE = int('0x0305000F', 16)
    MOVE_MODE_STEP = 4
    MOVE_MODE_DC_REL = 3
    MOVE_MODE_DC_ABS = 2
    SCALE = 65535
    DC_VEL_MIN = 100/56635
    DC_VEL_MAX = 10**8

    def __init__(self, logger=None):
        """ Instantiate Nanopositioners"""

        self.log = LogHandler(logger)

        # Loads Nanopositioners DLL and define arguments and result types for c function
        self._nanopositionersdll = ctypes.windll.LoadLibrary('SmarActCTL.dll')
        self._configure_functions()

        #Finds devices connected to controller
        buffer = ctypes.create_string_buffer(4096)  #the way to have a mutable buffer
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer)) #size _t gives c_ulonglong, not as in manual
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, buffer, buffersize)

        # Handle errors
        if result:
            msg_str = 'No MCS2 devices found'
            self.log.error(msg_str)
            raise(msg_str)

        #Establishes a connection to a device
        self.dev_name = buffer.value.decode("utf-8")
        dhandle =  ctypes.c_uint32()
        connect = self._nanopositionersdll.SA_CTL_Open(dhandle, buffer.value, None)
        if connect == 0:
            self.dhandle = dhandle.value
            self.log.info(f'Connected to device {self.dev_name} with handle {self.dhandle}')
        else:
            msg_str = f'Failed to connect to device {self.dev_name}'
            self.log.error(msg_str)
            raise(msg_str)

        # Get channel information
        channel_buffer = ctypes.c_int32()
        channel_buffer_size = ctypes.c_size_t(ctypes.sizeof(channel_buffer))
        channel_result = self._nanopositionersdll.SA_CTL_GetProperty_i32(
            self.dhandle, 0, self.PKEY_NUM_CH, channel_buffer, channel_buffer_size
        )
        self.num_ch = channel_buffer.value
        if channel_result == 0 and self.num_ch > 0:
            self.log.info(f'Found {self.num_ch} channels on {self.dev_name}')
        else:
            msg_str = f'Failed to find channels on {self.dev_name}'
            self.log.error(msg_str)
            raise(msg_str)

    def close(self):
        """ Closes connection to device"""

        connect = self._nanopositionersdll.SA_CTL_Close(self.dhandle)
        if connect:
            msg_str = f'Failed to properly close connection to {self.dev_name}'
            self.log.warn(msg_str)
        else:
            self.log.info(f'Disconnected from {self.dev_name}')

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        """ Sets parameters for motion

        Leave parameter as None in order to leave un-changed

        :param channel: (int) index of channel from 0 to self.num_ch
        :param mode: (str) default is 'step', can use 'dc', 'dc_rel' to set abs or rel DC voltage
        :param freq: (int) frequency in Hz from 1 to 20000
        :param amp: (float) amplitude in volts from 0 to 100
        :param dc_vel: (float) velocity for DC steps in volts/sec
        """

        # Set movement mode
        if mode is not None:
            if mode == 'dc':
                result_mode = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle, channel, self.PKEY_MOVE_MODE, self.MOVE_MODE_DC_ABS
                )
                if result_mode:
                    self.log.warn(
                        f'Failed to set mode to DC for positioner {self.dev_name},'
                        f' channel {channel}'
                    )
            elif mode == 'dc_rel':
                result_mode = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle, channel, self.PKEY_MOVE_MODE, self.MOVE_MODE_DC_REL
                )
                if result_mode:
                    self.log.warn(
                        f'Failed to set mode to DC for positioner {self.dev_name},'
                        f' channel {channel}'
                    )
            else:
                result_mode = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle, channel, self.PKEY_MOVE_MODE, self.MOVE_MODE_STEP
                )
                if result_mode:
                    self.log.warn(
                        f'Failed to set mode to step for positioner {self.dev_name},'
                        f' channel {channel}'
                    )

        # Set frequency
        if frequency is not None:

            # Check for reasonable range
            if 1 <= frequency <= 20000:
                result_freq = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle, channel, self.PKEY_STEP_FREQ, int(frequency)
                )
                if result_freq:
                    self.log.warn(
                        f'Failed to set step frequency to {frequency} for positioner '
                        f'{self.dev_name}, channel {channel}'
                    )

            # Handle out of range request
            else:
                self.log.warn('Warning, can only set frequency within 1 Hz and 20 kHz')

        # Set amplitude
        if amplitude is not None:

            # Check for reasonable range
            bit_amp = value_to_bitval(amplitude, bits=16, min=0, max=100)
            if 1 <= bit_amp <= 65535:
                result_amp = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle, channel, self.PKEY_STEP_AMP, bit_amp
                )
                if result_amp:
                    self.log.warn(
                        f'Failed to set step amplitude to {amplitude} for positioner '
                        f'{self.dev_name}, channel {channel}'
                    )
            else:
                self.log.warn('Warning, can only set amplitude in the range of 0 to 100 V')

        # Set DC velocity
        if dc_vel is not None:

            # Check for reasonable range
            bit_vel = int(dc_vel * (self.SCALE/100))
            if 1 <= bit_vel <= self.SCALE*10**6:
                result_vel = self._nanopositionersdll.SA_CTL_SetProperty_i64(
                    self.dhandle, channel, self.PKEY_DC_VEL, bit_vel
                )
                if result_vel:
                    self.log.warn(
                        f'Failed to set DC velocity to {dc_vel} V/s for positioner '
                        f'{self.dev_name}, channel {channel}'
                    )
            else:
                self.log.warn('Warning, can only set velocity in the range of '
                              f'{self.DC_VEL_MIN} to {self.DC_VEL_MAX} V/s')

    def get_voltage(self, channel):
        """ Returns the current DC voltage on a piezo

        :param channel: (int) channel index (from 0)
        """

        voltage_buffer = ctypes.c_int64()
        voltage_buffer_size = ctypes.c_size_t(ctypes.sizeof(voltage_buffer))
        voltage_result = self._nanopositionersdll.SA_CTL_GetProperty_i64(
            self.dhandle, channel, self.PKEY_VOLT, voltage_buffer, voltage_buffer_size
        )

        # Handle error
        if voltage_result:
            self.log.warn(f'Could not retrieve voltage for channel {channel}'
                          f'on device {self.dev_name}')

        return bitval_to_value(voltage_buffer.value, bits=16, min=0, max=100)

    def set_voltage(self, channel, voltage=50):
        """ Sets an absolute voltage to the piezo

        :param channel: (int) channel index (from 0)
        :param voltage: (float) voltage to set from 0 to 100 V (default is 50)
        """

        # Change the move mode to voltage absolute
        self.set_parameters(channel, mode='dc')

        # Move to desired voltage
        bit_voltage = value_to_bitval(voltage, bits=16, min=0, max=100)
        move_result = self._nanopositionersdll.SA_CTL_Move(
            self.dhandle, channel, bit_voltage, 0
        )

        # Check success
        if move_result:
            self.log.warn(
                f'Failed to set DC voltage to {voltage} V on channel {channel} of {self.dev_name}'
            )

    def n_steps(self, channel, n=1):
        """ Takes n steps

        :param channel: (int) channel index (from 0)
        :param n: (int) number of steps to take, negative is in opposite direction
        """

        # Take the step
        self.set_parameters(channel, mode='step')
        result_step = self._nanopositionersdll.SA_CTL_Move(self.dhandle, channel, n, 0)

        # Handle error
        if result_step:
            self.log.warn(f'Failed to take {n} steps on device {self.dev_name}, channel {channel}')

    def move(self, channel, backward=False):
        """ Takes the maximum number of steps (quasi continuous)

        :param channel: (int) channel index (from 0)
        :param backward: (bool) whether or not to step in backwards direction (default False)
        """

        # Configure move
        self.set_parameters(channel, mode='step')
        if backward:
            MOVE_STEPS = -100000
        else:
            MOVE_STEPS = 100000

        # Send move command
        result_move = self._nanopositionersdll.SA_CTL_Move(self.dhandle, channel, MOVE_STEPS, 0)

        # Handle error
        if result_move:
            self.log.warn(f'Failed to take move on device {self.dev_name}, channel {channel}')

    def stop(self, channel):
        """ Terminates any ongoing movement

        :param channel: (int) channel index (from 0)
        """

        result_stop = self._nanopositionersdll.SA_CTL_Stop(self.dhandle, channel, 0)
        if result_stop:
            self.log.warn(f'Failed to stop movement on device {self.dev_name}, channel {channel}')

    def is_moving(self, channel):
        """ Returns whether or not the positioner is moving

        :param channel: (int) channel index (from 0)

        :return: (bool) true if moving
        """

        # Get the state bit
        current_state_buffer = ctypes.c_int32()
        current_state_buffer_size = ctypes.c_size_t(ctypes.sizeof(current_state_buffer))
        state_result = self._nanopositionersdll.SA_CTL_GetProperty_i32(
            self.dhandle, channel, self.PKEY_CURRENT_STATE,
            current_state_buffer, current_state_buffer_size
        )

        # Handle an error
        if state_result:
            self.log.warn(f'Failed to check if positioner {self.dev_name} is moving on'
                          f'Channel {channel}')

        # Decode state bit
        if current_state_buffer.value % 2 == 0:
            return False
        else:
            return True


    # Technical methods

    def _configure_functions(self):
        """ Defines arguments and results for c functions """

        # Device connection, disconnection
        self._nanopositionersdll.SA_CTL_GetFullVersionString.restype = ctypes.c_char_p

        self._nanopositionersdll.SA_CTL_FindDevices.argtypes = [
            ctypes.c_char_p,                    # options for find procedure
            ctypes.POINTER(ctypes.c_char),      # pointer to buffer for writing device locator
            ctypes.POINTER(ctypes.c_ulonglong)  # pointer to variable holding size of buffer
        ]
        self._nanopositionersdll.SA_CTL_FindDevices.restype = ctypes.c_uint32   # result status

        self._nanopositionersdll.SA_CTL_Open.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),    # pointer to device handle for use in future calls
            ctypes.c_char_p,                    # device locator
            ctypes.c_char_p                     # config (unused)
        ]
        self._nanopositionersdll.SA_CTL_Open.restypes = ctypes.c_uint32 # result status

        self._nanopositionersdll.SA_CTL_Close.argtype = ctypes.c_uint32 # device handle
        self._nanopositionersdll.SA_CTL_Close.restype = ctypes.c_uint32 # result status

        # Getting device properties
        self._nanopositionersdll.SA_CTL_GetProperty_i32.argtypes = [
            ctypes.c_uint32,                # device handle
            ctypes.c_int8,                  # index of addressed device, module, or channel
            ctypes.c_uint32,                # property key
            ctypes.POINTER(ctypes.c_int32), # pointer to buffer where result is written
            ctypes.POINTER(ctypes.c_ulonglong) # pointer to size of value buffer (number of elements)
        ]
        self._nanopositionersdll.SA_CTL_GetProperty_i32.restype = ctypes.c_uint32   # result status

        self._nanopositionersdll.SA_CTL_GetProperty_i64.argtypes = [
            ctypes.c_uint32,                    # device handle
            ctypes.c_int8,                      # index of addressed device, module, or channel
            ctypes.c_uint32,                    # property key
            ctypes.POINTER(ctypes.c_int64),     # pointer to buffer where result is written
            ctypes.POINTER(ctypes.c_ulonglong)  # pointer to size of value buffer (# of elements)
        ]
        self._nanopositionersdll.SA_CTL_GetProperty_i64.restype = ctypes.c_uint32   # result status

        # Settting device properties
        self._nanopositionersdll.SA_CTL_SetProperty_i32.argtypes = [
            ctypes.c_uint32,    # device handle
            ctypes.c_int8,      # index of addressed device, module, or channel
            ctypes.c_uint32,    # property key
            ctypes.c_int32,     # value to write
        ]
        self._nanopositionersdll.SA_CTL_SetProperty_i32.restype = ctypes.c_uint32   # result status

        self._nanopositionersdll.SA_CTL_SetProperty_i64.argtypes = [
            ctypes.c_uint32,    # device handle
            ctypes.c_int8,      # index of addressed device, module, or channel
            ctypes.c_uint32,    # property key
            ctypes.c_int64      # value to write
        ]
        self._nanopositionersdll.SA_CTL_SetProperty_i64.restype = ctypes.c_uint32   # result status

        # Movement
        self._nanopositionersdll.SA_CTL_Move.argtypes = [
            ctypes.c_uint32,    # device handle
            ctypes.c_int8,      # index of addressed device, module, or channel
            ctypes.c_int64,     # move value
            ctypes.c_uint32     # transmit handle
        ]
        self._nanopositionersdll.SA_CTL_Move.restype = ctypes.c_uint32  # result status

        self._nanopositionersdll.SA_CTL_Stop.argtypes = [
            ctypes.c_uint32,    # device handle
            ctypes.c_int8,      # index of addressed device, module, or channel
            ctypes.c_uint32     # transmit handle
        ]
        self._nanopositionersdll.SA_CTL_Stop.restype = ctypes.c_uint32  # result status
