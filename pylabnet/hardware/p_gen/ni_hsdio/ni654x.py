import ctypes
from pylabnet.hardware.p_gen.ni_hsdio import NI_HSDIO_DLL_PATH
from pylabnet.hardware.p_gen.ni_hsdio.c_headers import NITypes, NIConst, build_c_func_prototypes
from pylabnet.logic.pulsed.pb_sample import pb_sample
from pylabnet.utils.logging.logger import LogHandler
import numpy as np
import copy


class NI654x:
    def __init__(self, dev_name_str, logger=None):

        #
        # Define internal variables
        #

        self.log = LogHandler(logger=logger)
        self.map_dict = dict()
        self.writn_wfm_set = set()

        #
        # "Load" niHSDIO DLL
        #

        try:
            self.dll = ctypes.WinDLL(NI_HSDIO_DLL_PATH)
        except OSError:
            msg_str = 'DLL loading failed. \n' \
                      'Ensure that niHSDIO DLL path is correct: \n' \
                      'it should be specified in pylabnet.hardware.p_gen.ni_hsdio.__init__.py \n' \
                      'Current value is: \n' \
                      '"{}"'.format(NI_HSDIO_DLL_PATH)
            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

        # Build C-prototypes (in particular, specify the return
        # types such that Python reads results correctly)
        build_c_func_prototypes(self.dll)

        #
        # Connect to device
        #

        # Create blank session handle
        self._handle = NITypes.ViSession()

        # Convert dev_name to the DLL-readable format
        self._dev_name = NITypes.ViRsrc(
            dev_name_str.encode('ascii')
        )

        self._er_chk(
            self.dll.niHSDIO_InitGenerationSession(
                self._dev_name,             # ViRsrc resourceName
                NIConst.VI_TRUE,            # ViBoolean IDQuery
                NIConst.VI_TRUE,            # ViBoolean resetDevice
                NIConst.VI_NULL,            # ViConstString optionString - not used, set to VI_NULL
                ctypes.byref(self._handle)  # ViSession * session_handle
            )
        )

        # Log info message
        serial_str = self._get_attr_str(
            NIConst.NIHSDIO_ATTR_SERIAL_NUMBER
        )
        self.log.info(
            'Connected to NI HSDIO card {0}. Serial number: {1}. Session handle: {2}'
            ''.format(dev_name_str, serial_str, self._handle)
        )

    def reset(self):

        self.writn_wfm_set = set()

        return self._er_chk(
            self.dll.niHSDIO_reset(self._handle)
        )

    def start(self):
        return self._er_chk(
            self.dll.niHSDIO_Initiate(
                self._handle
            )
        )

    def stop(self):
        return self._er_chk(
            self.dll.niHSDIO_Abort(
                self._handle
            )
        )

    def disconnect(self):
        self.reset()

        op_status = self._er_chk(
            self.dll.niHSDIO_close(self._handle)
        )
        return op_status

    # ================================================================
    # Hardware settings
    # ================================================================

    def get_samp_rate(self):
        return self._get_attr_real64(
            NIConst.NIHSDIO_ATTR_SAMPLE_CLOCK_RATE
        )

    def set_samp_rate(self, samp_rate):

        # Sanity check
        if not samp_rate <= self.constraints['samp_rate']['max']:
            self.log.warn(
                'set_samp_rate({0} MHz): the requested value exceeds hardware constraint max={1} MHz.\n'
                'The max possible value will be set instead.'
                ''.format(samp_rate / 1e6, self.constraints['samp_rate']['max'] / 1e6)
            )
            samp_rate = self.constraints['samp_rate']['max']

        elif not self.constraints['samp_rate']['min'] <= samp_rate:
            self.log.warn(
                'set_samp_rate({0} Hz): the requested value is below the hardware constraint min={1} Hz.\n'
                'The min possible value will be set instead.'
                ''.format(samp_rate, self.constraints['samp_rate']['min'])
            )
            samp_rate = self.constraints['samp_rate']['min']

        # Call DLL function
        # Currently, the onboard clock is used as the sample clock source
        self._er_chk(
            self.dll.niHSDIO_ConfigureSampleClock(
                self._handle,                            # ViSession vi
                NIConst.NIHSDIO_VAL_ON_BOARD_CLOCK_STR,  # ViConstString clockSource
                NITypes.ViReal64(samp_rate)              # ViReal64 clockRate
            )
        )

        # Return the actual final sample rate
        return self.get_samp_rate()

    def get_active_chs(self):
        return self._get_attr_str(
            NIConst.NIHSDIO_ATTR_DYNAMIC_CHANNELS
        )

    def set_active_chs(self, chs_str=None):

        if chs_str is None:
            # un-assign all channels
            chs_str = 'none'

        chs_str = NITypes.ViString(chs_str.encode('ascii'))

        self._er_chk(
            self.dll.niHSDIO_AssignDynamicChannels(
                self._handle,  # ViSession vi,
                chs_str        # ViConstString channelList
            )
        )

        return self.get_active_chs()

    def get_mode(self):
        """

        :return: (str) "W" - Waveform, "S" - Scripted
        """

        mode_id = self._get_attr_int32(
            attr_id=NIConst.NIHSDIO_ATTR_GENERATION_MODE
        )

        if mode_id == NIConst.NIHSDIO_VAL_WAVEFORM.value:
            return 'W'
        elif mode_id == NIConst.NIHSDIO_VAL_SCRIPTED.value:
            return 'S'
        else:
            msg_str = 'get_mode(): self._get_attr_int32(NIHSDIO_ATTR_GENERATION_MODE) ' \
                      'returned unknown mode_id = {0}'.format(mode_id)
            self.log.error(msg_str)
            raise NIHSDIOError(msg_str)

    def set_mode(self, mode_string):
        """

        :param mode_string: (str) "W" - Waveform, "S" - Scripted
        :return: actual run mode string ("W"/"S")
        """

        if mode_string == 'W':
            run_mode = NIConst.NIHSDIO_VAL_WAVEFORM
        elif mode_string == 'S':
            run_mode = NIConst.NIHSDIO_VAL_SCRIPTED
        else:
            msg_str = 'set_mode({0}): invalid argument. Valid values: "W" - Waveform, "S" - scripted. \n' \
                      'Run mode was not changed. Actual run mode string was returned.'.format(mode_string)

            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

        # Call DLL function
        self._er_chk(
            self.dll.niHSDIO_ConfigureGenerationMode(
                self._handle,  # ViSession vi
                run_mode       # ViInt32 generationMode
            )
        )

        # Return actual run mode
        return self.get_mode()

    @property
    def constraints(self):

        # Total memory size
        # [in samples; one sample contains 32 bits and covers all channels]
        max_wfm_len = self._get_attr_int32(
            attr_id=NIConst.NIHSDIO_ATTR_TOTAL_GENERATION_MEMORY_SIZE
        )

        constr_dict = dict(
            samp_rate=dict(
                min=48,
                max=100e6
            ),
            wfm_len=dict(
                min=2,
                step=2,
                max=max_wfm_len
            )
        )

        return constr_dict

    def get_status(self):

        try:
            # Record current samp_rate to restore it later
            current_rate = self.get_samp_rate()
            rate_lims = self.constraints['samp_rate']

            test_rate = (rate_lims['min'] + rate_lims['max']) / 2

            # Try changing samp_rate
            op_status = self.dll.niHSDIO_ConfigureSampleClock(
                self._handle,                            # ViSession vi
                NIConst.NIHSDIO_VAL_ON_BOARD_CLOCK_STR,  # ViConstString clockSource
                NITypes.ViReal64(test_rate)              # ViReal64 clockRate
            )

            # If device is idle, operation should be successful:
            #   op_status = 0.
            # Restore original samp rate and return 0 - "idle"

            if op_status == 0:
                self.set_samp_rate(samp_rate=current_rate)
                return 0

            # If device is running, attempt to change samp_rate should return
            # the following error code:
            #   -1074118617
            #   "Specified property cannot be set while the session is running.
            #   Set the property prior to initiating the session,
            #   or abort the session prior to setting the property."

            elif op_status == -1074118617:
                # Device is running
                return 1

            # This method cannot interpret any other error/warning code and has
            # to raise an exception

            else:
                raise NIHSDIOError(
                    'get_status(): the attempt to test-change samp_rate returned unknown error code {}'
                    ''.format(op_status)
                )

        # If connection to the device is lost
        # or any operation fails, raise an exception.

        except Exception as exc_obj:
            self.log.exception(
                'get_status(): an exception was produced. \n'
                'This might mean that connection to the device is lost '
                'or there is some bug in the get_status() method. \n'
            )
            raise exc_obj

    # ================================================================
    # Waveform Generation
    # ================================================================

    def write_wfm(self, pb_obj, step_adj=True):

        #
        # Sanity checks
        #

        # Only data_width=32 write is currently implemented
        # (DLL function niHSDIO_WriteNamedWaveformU32)
        hrdw_data_width = 8 * self._get_attr_int32(NIConst.NIHSDIO_ATTR_DATA_WIDTH)
        if hrdw_data_width != 32:
            msg_txt = 'write_wfm(): the card you use has data_width = {0} bits. \n' \
                      'The method was written assuming 32-bit width and have to be modified for your card. \n' \
                      'Rewrite bit_ar construction part and use niHSDIO_WriteNamedWaveformU{1}() DLL function' \
                      ''.format(hrdw_data_width, hrdw_data_width)

            self.log.error(msg_txt)
            raise NIHSDIOError(msg_txt)

        #
        # Sample PulseBlock
        #

        # Map user-friendly names onto physical channel numbers
        pb_obj = copy.deepcopy(pb_obj)
        pb_obj.ch_map(map_dict=self.map_dict)

        # Sample pulse block
        samp_rate = self.get_samp_rate()
        samp_dict, n_pts, add_pts = pb_sample(
            pb_obj=pb_obj,
            samp_rate=samp_rate,
            len_min=self.constraints['wfm_len']['min'],
            len_max=self.constraints['wfm_len']['max'],
            len_step=self.constraints['wfm_len']['step'],
            step_adj=step_adj
        )
        wfm_name = pb_obj.name
        del pb_obj

        self.log.info(
            'write_wfm(): sampled PulseBlock "{}". \n'
            'Sample array has {} points. {} samples were added to match hardware wfm len step'
            ''.format(wfm_name, n_pts, add_pts)
        )

        #
        # Pack samp_dict into bit_ar
        #

        # Create a blank bit_ar - all elements zero (all channels off)
        bit_ar = np.zeros(shape=n_pts, dtype=np.uint32)

        # Iterate through each channel and set corresponding bit to '1'
        # if value is True
        for ch_num in samp_dict.keys():

            # This number in uint32 representation has all zeros and
            # exactly one '1' at the ch_num-th bit from the LSB
            ch_bit_one = 2**ch_num

            for idx, val in enumerate(samp_dict[ch_num]):
                if val:
                    bit_ar[idx] += ch_bit_one

            # TODO: consider making very fast with numpy:
            # ch_bit_ar = samp_dict[ch_num].astype(int) * 2**ch_num
            # bit_ar = np.add(bit_ar, ch_bit_ar)

        #
        # Load bit_ar to memory
        #

        # Delete waveform with the same name,
        # if it is already present in the memory
        if wfm_name in self.writn_wfm_set:
            self.del_wfm(wfm_name=wfm_name)

        # Create C-pointer to bit_ar using numpy.ndarray.ctypes attribute
        bit_ar_ptr = bit_ar.ctypes.data_as(
            ctypes.POINTER(NITypes.ViUInt32)
        )

        # Call DLL function
        self._er_chk(
            self.dll.niHSDIO_WriteNamedWaveformU32(
                self._handle,                                     # ViSession vi
                NITypes.ViConstString(wfm_name.encode('ascii')),  # ViConstString waveformName
                NITypes.ViInt32(n_pts),                           # ViInt32 samplesToWrite
                bit_ar_ptr                                        # ViUInt32 data[]
            )
        )

        self.writn_wfm_set.add(wfm_name)

        return 0

    def del_wfm(self, wfm_name):
        self._er_chk(
            self.dll.niHSDIO_DeleteNamedWaveform(
                self._handle,                                    # ViSession vi
                NITypes.ViConstString(wfm_name.encode('ascii'))  # ViConstString waveformName
            )
        )

        self.writn_wfm_set.remove(wfm_name)

        return 0

    def clr_mem(self):
        wfm_set = copy.deepcopy(self.writn_wfm_set)

        for wfm_name in wfm_set:
            self.del_wfm(wfm_name=wfm_name)

        return 0

    def get_rep(self):
        """Returns number of repetitions in Waveform generation mode.

        On the hardware level, it is just a pair of attributes
        NIHSDIO_ATTR_REPEAT_MODE and NIHSDIO_ATTR_REPEAT_COUNT
        which are not bound to any specific waveform.

        :return: (int) repeat mode + number of repetitions:
                 0 - repeat infinitely
                 positive integer - finite, number of repetitions
                 NIHSDIOError exception - error
        """

        rep_mode = self._get_attr_int32(
            NIConst.NIHSDIO_ATTR_REPEAT_MODE
        )

        if rep_mode == NIConst.NIHSDIO_VAL_CONTINUOUS.value:
            rep_num = 0
        elif rep_mode == NIConst.NIHSDIO_VAL_FINITE.value:
            rep_num = self._get_attr_int32(
                NIConst.NIHSDIO_ATTR_REPEAT_COUNT
            )
        else:
            msg_str = 'get_rep(): DLL call returned unknown repetition mode code {}'.format(rep_mode)

            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

        return rep_num

    def set_rep(self, rep_num):
        """Set repeat mode and number of repetitions

        :param rep_num: (int) repeat mode + number of repetitions:
                    0 - repeat infinitely
                    positive integer - finite, number of repetitions

        :return: (int) actual repeat mode + number of repetitions:
                    0 - repeat infinitely
                    positive integer - finite, number of repetitions
                    NIHSDIOError exception - error
        """

        if rep_num == 0:
            rep_mode = NIConst.NIHSDIO_VAL_CONTINUOUS
            rep_num = NIConst.VI_NULL

        elif rep_num > 0:
            rep_mode = NIConst.NIHSDIO_VAL_FINITE
            rep_num = NITypes.ViInt32(rep_num)

        else:
            msg_str = 'set_rep() invalid argument {} \n' \
                      'Valid values: 0 - infinite, positive integer - finite' \
                      ''.format(rep_num)

            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

        self._er_chk(
            self.dll.niHSDIO_ConfigureGenerationRepeat(
                self._handle,  # ViSession vi
                rep_mode,      # ViInt32 repeatMode
                rep_num        # ViInt32 repeatCount
            )
        )

        return self.get_rep()

    def get_wfm_to_gen(self):
        return self._get_attr_str(
            NIConst.NIHSDIO_ATTR_WAVEFORM_TO_GENERATE
        )

    def set_wfm_to_gen(self, wfm_name):
        self._er_chk(
            self.dll.niHSDIO_ConfigureWaveformToGenerate(
                self._handle,                                    # ViSession vi
                NITypes.ViConstString(wfm_name.encode('ascii'))  # ViConstString waveformName
            )
        )
        return self.get_wfm_to_gen()

    # ================================================================
    # Script Generation
    # ================================================================

    def write_script(self, script_str):

        # Sanity check: script_str is a string
        if not isinstance(script_str, str):
            msg_str = 'write_script(): passed argument is not a string'

            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

        plain_script_str = script_str.replace('\n', ' ')

        # Convert into C-string
        c_script_str = NITypes.ViConstString(
            plain_script_str.encode('ascii')
        )

        op_status = self._er_chk(
            self.dll.niHSDIO_WriteScript(
                self._handle,  # ViSession vi
                c_script_str   # ViConstString script
            )
        )

        return op_status

    def get_scr_to_gen(self):
        return self._get_attr_str(
            NIConst.NIHSDIO_ATTR_SCRIPT_TO_GENERATE
        )

    def set_scr_to_gen(self, script_name):

        # Convert script_name into C-string
        script_name = NITypes.ViConstString(
            script_name.encode('ascii')
        )

        self._er_chk(
            self.dll.niHSDIO_ConfigureScriptToGenerate(
                self._handle,  # ViSession vi
                script_name    # ViConstString scriptName
            )
        )

        return self.get_scr_to_gen()

    # ================================================================
    # Wrappers for C DLL helper functions
    # ================================================================

    def _er_chk(self, error_code):
        # C:\Program Files\National Instruments\Shared\Errors\English\IVI-errors.txt

        if error_code == 0:
            # Success
            return 0
        else:
            # Warning or Error

            # Create buffer for DLL function to output the error message string
            msg_buf = ctypes.create_string_buffer(256)

            # Call DLL function to generate readable error message
            self.dll.niHSDIO_error_message(
                self._handle,                  # ViSession vi
                NITypes.ViStatus(error_code),  # ViStatus errorCode
                msg_buf                        # ViChar errorMessage[256]
            )
            msg_str = msg_buf.value.decode('ascii')

            if error_code > 0:
                # Warning
                self.log.warn(msg_str=msg_str)
                return error_code
            else:
                # Error
                self.log.error(msg_str=msg_str)
                raise NIHSDIOError(msg_str)

    def _get_attr_int32(self, attr_id, ch=None):
        """

        :param attr_id:
        :param ch: (int)
        :return: (int) obtained value in the case of success
                 NIHSDIOError exception is produced in the case of error
        """

        # Create buffer where niHSDIO_GetAttribute will store the result
        buf = NITypes.ViInt32()

        # Convert channel number into C-string
        # (used to request channel-agnostic/-specific attributes)
        if ch is None:
            ch_str = NIConst.VI_NULL
        else:
            ch_str = str(ch)
            # Convert into C-string
            ch_str = ctypes.c_char_p(ch_str.encode('ascii'))

        # Call DLL function
        try:
            self._er_chk(
                self.dll.niHSDIO_GetAttributeViInt32(
                    self._handle,      # ViSession vi
                    ch_str,            # ViConstString channelName
                    attr_id,           # ViAttr attribute
                    ctypes.byref(buf)  # ViInt32 *value
                )
            )
            return buf.value

        except OSError:
            # DLL normally handles all "moderate" errors and returns error code,
            # which is being analyzed by self._er_chk.
            # "try" handles OSError when the DLL function fails completely
            # and isn't able to handle the error by itself

            msg_str = '_get_attr_int32(): OSError, DLL function call failed'
            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

    def _get_attr_str(self, attr_id, ch=None):
        """

        :param attr_id:
        :param ch: (int)
        :return: (str) obtained value in the case of success
                       Exception is produced in the case of error
        """

        # Create buffer where niHSDIO_GetAttribute will store the result
        buf_size = 1024  # Buffer size of 1024 was chosen for no specific reason. Increase if needed.
        buf = ctypes.create_string_buffer(buf_size)

        # Convert channel number into C-string
        # (used to request channel-agnostic/-specific attributes)
        if ch is None:
            ch_str = NIConst.VI_NULL
        else:
            ch_str = str(ch)
            # Convert into C-string
            ch_str = ctypes.c_char_p(ch_str.encode('ascii'))

        # Call DLL function
        try:
            self._er_chk(
                self.dll.niHSDIO_GetAttributeViString(
                    self._handle,               # ViSession vi
                    ch_str,                     # ViConstString channelName
                    attr_id,                    # ViAttr attribute
                    NITypes.ViInt32(buf_size),  # ViInt32 bufSize
                    buf                         # ViChar value[]
                )
            )
            return buf.value.decode('ascii')

        except OSError:
            # DLL normally handles all "moderate" errors and returns error code,
            # which is being analyzed by self._er_chk.
            # "try" handles OSError when the DLL function fails completely
            # and isn't able to handle the error by itself

            msg_str = '_get_attr_str(): OSError, DLL function call failed'
            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)

    def _get_attr_real64(self, attr_id, ch=None):
        """

        :param attr_id:
        :param ch: (int)
        :return: (float) obtained value in the case of success
                 Exception is produced in the case of error
        """

        # Create buffer where niHSDIO_GetAttribute will store the result
        buf = NITypes.ViReal64()

        # Convert channel number into C-string
        # (used to request channel-agnostic/-specific attributes)
        if ch is None:
            ch_str = NIConst.VI_NULL
        else:
            ch_str = str(ch)
            # Convert into C-string
            ch_str = ctypes.c_char_p(ch_str.encode('ascii'))

        # Call DLL function
        try:
            self._er_chk(
                self.dll.niHSDIO_GetAttributeViReal64(
                    self._handle,      # ViSession vi
                    ch_str,            # ViConstString channelName
                    attr_id,           # ViAttr attribute
                    ctypes.byref(buf)  # ViReal64 *value
                )
            )
            return buf.value

        except OSError:
            # DLL normally handles all "moderate" errors and returns error code,
            # which is being analyzed by self._er_chk.
            # "try" handles OSError when the DLL function fails completely
            # and isn't able to handle the error by itself

            msg_str = '_get_attr_real64(): OSError, DLL function call failed'
            self.log.error(msg_str=msg_str)
            raise NIHSDIOError(msg_str)


class NIHSDIOError(Exception):
    pass
