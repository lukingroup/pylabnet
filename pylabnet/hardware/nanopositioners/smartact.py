import ctypes

from pylabnet.utils.logging.logger import LogHandler


class Nanopositioners():

    # property keys and other constants
    PKEY_NUM_BUS = int("0x020F0016",16)
    PKEY_NUM_CH = int('0x020F0017', 16)
    PKEY_NUM_BUS_CH = int('0x02030017', 16)
    PKEY_MOVE_MODE = int('0x03050087', 16)
    MOVE_MODE_STEP = 4
    MOVE_MODE_DC = 3

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

    def move(self):

        #defines arguments and results for c functions in move function
        self._nanopositionersdll.SA_CTL_SetProperty_i32.argtypes = [ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_int8),ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_int32)]
        #self._nanopositionersdll.SA_CTL_SetProperty_i32.restype = ctypes.POINTER(ctypes.c_uint32)
        #self._nanopositionersdll.SA_CTL_Move.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_int8), ctypes.POINTER(ctypes.c_int64),ctypes.POINTER(ctypes.c_uint32)]
        #self._nanopositionersdll.SA_CTL_Stop.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint32)]

        #define movement parameters to input in c functions
        channel = ctypes.c_int8(0)
        stepmode = ctypes.c_int32(4)
        #stepnumber = ctyeps.uint64(1)
        freq = ctypes.c_int32(100)
        amp = ctypes.c_int32(100)

        # set mode to relative movement and define frequency and amplitude
        resultmode = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, modetype, stepmode) #define move mode SA_CTL_MOVE_MODE_STEP
        resultfreq = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, profreq, freq)
        resultamp = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, proamp,  amp)

        #move command to positioner in a specific channel
        #moveresult = self._nanopositionersdll.SA_CTL_Move(self.dhandle, channel, stepnumber, 0)
        #if moveresult == 0:
        #    print('Positioner moving in channel ' + str(channel))

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None):
        """ Sets parameters for motion

        Leave parameter as None in order to leave un-changed
        :param channel: (int) index of channel from 0 to self.num_ch
        :param mode: (str) default is 'step', can use 'dc' to set DC voltage
        :param freq:
        :param amp:
        """

        if mode is not None:
            if mode == 'dc':
                result_mode = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle,
                    channel,
                    self.PKEY_MOVE_MODE,
                    self.MOVE_MODE_DC
                )
                if result_mode:
                    self.log.warn(
                        f'Failed to set mode to DC for positioner {self.dev_name},'
                        f'channel {channel}'
                    )
            else:
                result_mode = self._nanopositionersdll.SA_CTL_SetProperty_i32(
                    self.dhandle,
                    channel,
                    self.PKEY_MOVE_MODE,
                    self.MOVE_MODE_STEP
                )
                if result_mode:
                    self.log.warn(
                        f'Failed to set mode to step for positioner {self.dev_name},'
                        f'channel {channel}'
                    )

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

        # Settting device properties
        self._nanopositionersdll.SA_CTL_SetProperty_i32.argtypes = [
            ctypes.c_uint32,    # device handle
            ctypes.c_int8,      # index of addressed device, module, or channel
            ctypes.c_uint32,    # property key
            ctypes.c_int32,     # value to write
        ]
        self._nanopositionersdll.SA_CTL_SetProperty_i32.restype = ctypes.c_uint32   # result status

    def _get_module_info(self):
        """ Gets baseline device properties """

        bus_buffer = ctypes.c_int32()
        bus_buffer_size = ctypes.c_size_t(ctypes.sizeof(bus_buffer))
        bus_result = self._nanopositionersdll.SA_CTL_GetProperty_i32(
            self.dhandle, 0, self.PKEY_NUM_BUS, bus_buffer, bus_buffer_size
        )

        channel_buffer = ctypes.c_int32()
        channel_buffer_size = ctypes.c_size_t(ctypes.sizeof(channel_buffer))
        channel_result = self._nanopositionersdll.SA_CTL_GetProperty_i32(
            self.dhandle.value, 0, self.PKEY_NUM_CH, channel_buffer, channel_buffer_size
        )

        bus_channel_buffer = ctypes.c_int32()
        bus_channel_buffer_size = ctypes.c_size_t(ctypes.sizeof(bus_channel_buffer))
        bus_channel_result = self._nanopositionersdll.SA_CTL_GetProperty_i32(
            self.dhandle, 3, self.PKEY_NUM_BUS_CH, bus_channel_buffer, bus_channel_buffer_size
        )

        pass


def main():
    nanopos = Nanopositioners()
    nanopos.set_parameters(channel=0, mode='step')
    nanopos.close()

if __name__ == "__main__":

    main()




