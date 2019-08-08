# TODO: implement Dynamic Jump sequence mode
# TODO: implement (write_)sub-sequence mode
# TODO: inclulde proper routine to check and change zeroing functionality

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.simple_p_gen import PGenError
import pylabnet.logic.pulsed.pulse as po
from pylabnet.logic.pulsed.pb_sample import pb_sample

import os
import time
import visa
import numpy as np
from ftplib import FTP
from collections import OrderedDict
import copy


class TekAWG7k:
    """ A hardware module for the Tektronix AWG7000 series for generating
    waveforms and sequences thereof.

    Adapted from github.com/Ulm-IQO/qudi.
    """

    def __init__(self,
                 visa_adr_str, ftp_ip_str,
                 ftp_username=None, ftp_pswrd=None,
                 local_wfm_dir='user\\local_wfm_dir',
                 remote_wfm_dir='remote_wfm_dir',
                 visa_timeout=10,
                 logger=None):

        self.log = LogHandler(logger=logger)

        # Declaration of internal variables -----------------------------------

        self._awg = None  # This variable will hold a reference to the awg visa resource

        self.option_list = list()  # will hold the encoded installed options available on _awg
        self.model = None
        self._local_wfm_dir = None
        self._ftp_ip_str = None
        self._ftp_username = None
        self._ftp_pswrd = None
        self._written_seqs = []  # Helper variable since written sequences can not be queried
        self._loaded_seqs = []  # Helper variable since a loaded sequence can not be queried :(
        self._marker_byte_dict = {0: b'\x00', 1: b'\x01', 2: b'\x02', 3: b'\x03'}
        self._event_triggers = {'OFF': 'OFF', 'ON': 'ON'}

        # VISA connection -----------------------------------------------------

        self._rm = visa.ResourceManager()
        try:
            self._awg = self._rm.open_resource(visa_adr_str)
            # set timeout (in ms)
            self._awg.timeout = visa_timeout * 1000
        except:
            self._awg = None

            msg_str = 'VISA connection to address {} failed'.format(visa_adr_str)

            self.log.exception(msg_str=msg_str)
            raise PGenError(msg_str)

        # FTP connection ------------------------------------------------------

        # FTP (File Transfer Protocol) is used to transfer large waveform
        # from PC's hard drive to AWG's hard drive:
        #   - PulseBlock is sampled and the binary is stored in local_wfm_dir
        #   - FTP transfers file to remote_wfm_dir on AWG's hard drive
        #   - AWG loads the wfm into fast memory

        self._ftp_ip_str = ftp_ip_str
        self._ftp_username = ftp_username
        self._ftp_pswrd = ftp_pswrd
        self._remote_wfm_dir = remote_wfm_dir

        # Test FTP connection and set current working dir to remote_wfm_dir
        try:
            with FTP(ftp_ip_str) as ftp:
                ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
                ftp.cwd(self._remote_wfm_dir)
                self.log.debug('FTP connection test. Working dir: {0}'.format(ftp.pwd()))
        except:
            msg_str = 'Attempt to establish FTP connection failed. \n' \
                      'The following params where used: \n' \
                      '     ftp_ip_str = {} \n' \
                      '     ftp_username = {} \n' \
                      '     ftp_pswrd = {} \n' \
                      '     remote_wfm_dir = {}' \
                      ''.format(ftp_ip_str, ftp_username, ftp_pswrd, remote_wfm_dir)

            self.log.exception(msg_str=msg_str)
            raise PGenError(msg_str)

        # Create local_wfm_dir
        if local_wfm_dir == 'user\\local_wfm_dir':
            local_wfm_dir = os.path.expanduser('~\\local_wfm_dir')

        if not os.path.exists(local_wfm_dir):
            os.makedirs(os.path.abspath(local_wfm_dir))

        self._local_wfm_dir = local_wfm_dir

        # Set AWG current working dir to 'C:\\inetpub\\ftproot\remote_wfm_dir'
        self.write(
            'MMEM:CDIR "{0}"'.format(
                os.path.join('C:\\inetpub\\ftproot', remote_wfm_dir)
            )
        )
        self.query('*OPC?')

        # Determine device params ---------------------------------------------

        # Get model and option list
        mfg, self.model, ser, fw_ver = self.query('*IDN?').split(',')
        self.option_list = self.query('*OPT?').split(',')
        # Options of AWG7000 series:
        #              Option 01: Memory expansion to 64,8 MSamples (Million points)
        #              Option 06: Interleave and extended analog output bandwidth
        #              Option 08: Fast sequence switching
        #              Option 09: Subsequence and Table Jump

        # Log confirmation info message ---------------------------------------
        self.log.info(
            'Found {} {} Serial: {} FW: {} \n'
            'Installed options: {}'.format(
                mfg, self.model, ser, fw_ver, self.option_list
            )
        )

        self.raise_errors()

    def close(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        # Closes the connection to the AWG
        try:
            self._awg.close()
        except:
            self.log.debug('Closing AWG connection using pyvisa failed.')

        self.log.info('Closed connection to AWG')

        return 0

    # -------------------------------------------------------------------------
    # Basic commands and Hardware settings
    # -------------------------------------------------------------------------

    # Basic commands ----------------------------------------------------------

    def write(self, cmd_str):
        """ Sends a command string to the device.

        Should only be used for non-responding (set-type) commands!
        If the command is supposed to produce some response message,
        use query() method.

        @param string cmd_str: string containing the command
        @return int: error code (0:OK, -1:error)
        """

        bytes_written, status_code = self._awg.write(cmd_str)
        self._awg.write('*WAI')

        return status_code

    def query(self, question):
        """ Query the device:
            write request, read response, return formatted answer.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """

        answer = self._awg.query(question)
        answer = answer.strip()
        answer = answer.rstrip('\n')
        answer = answer.rstrip()
        answer = answer.strip('"')
        return answer

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """

        self.write('*RST')
        self.query('*OPC?')  # block and wait until the operation is complete

        # Clear status register
        self.write('*CLS')
        self.query('*OPC?')  # block and wait until the operation is complete

        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        -1: 'Failed Request or Communication'
         0: 'Device has stopped, but can receive commands'
         1: 'Device is waiting for trigger'
         2: 'Device is active and running'

        @return (int, dict): inter value of the current status with the
                             corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware
        """

        current_status = -1 if self._awg is None else int(self.query('AWGC:RST?'))
        return current_status

    def start(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        # Switch outputs on
        # (here it is assumed that all analog channels have a waveform
        # assigned, such that all channels are switched on)
        for ch in self._get_all_anlg_chs():
            ch_num = int(ch.rsplit('_ch', 1)[1])
            self.write(
                'OUTPUT{}:STATE ON'.format(ch_num)
            )
            self.query('*OPC?')

        # Start generator
        self.write('AWGC:RUN')
        self.query('*OPC?')

        self.raise_errors()
        return 0

    def stop(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.write('AWGC:STOP')
        self.query('*OPC?')

        for ch in self._get_all_anlg_chs():
            ch_num = int(ch.rsplit('_ch', 1)[1])
            self.write(
                'OUTPUT{0:d}:STATE OFF'.format(ch_num)
            )
            self.query('*OPC?')

        self.raise_errors()
        return 0

    def raise_errors(self):
        """Get all errors from the device and log them.

        :param level: (str) determines the level of the produced log entry:
                            'err' - the error messages will be logged as errors
                                    and PGenError exception will be produced
                            'warn' - as warnings

        :return: (bool) whether any error was found
        """

        # Get all errors
        read_next_err = True
        has_error = False

        msg_str_list = []

        while read_next_err:
            err = self.query('SYST:ERR?').split(',')

            if int(err[0]) == 0:
                read_next_err = False
            else:
                has_error = True
                msg_str_list.append(
                    '{} {}'.format(err[0], err[1])
                )

        # Log/raise if there are some errors
        if has_error:

            # Combine all error messages into a single string
            # with one error per line
            msg_str = '\n'.join(msg_str_list)

            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        return 0

    # Hardware settings -------------------------------------------------------

    def get_mode(self):
        """
        Returns AWG run mode according to the following list:
            continuous - 'C'
            triggered  - 'T'
            gated      - 'G'
            sequence   - 'S'
        @return str: 'C', 'T', 'G', 'S'.
        """

        run_mode_dict = {'CONT': 'C', 'TRIG': 'T', 'GAT': 'G', 'SEQ': 'S'}

        answer = self.query('AWGC:RMOD?')
        if answer in run_mode_dict:
            return run_mode_dict[answer]
        else:
            msg_str = 'get_mode(): returned answer {} is not on the list of known run modes' \
                      ''.format(answer)
            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

    def set_mode(self, mode_str):
        """Change the run mode of the AWG5000 series.

        @param str mode_str: Options for mode (case-insensitive):
                            continuous - 'C'
                            triggered  - 'T'
                            gated      - 'G'
                            sequence   - 'S'
        """

        look_up_dict = {
            'C': 'CONT',
            'T': 'TRIG',
            'G': 'GAT',
            'E': 'ENH',
            'S': 'SEQ'
        }
        self.write(
            'AWGC:RMOD {0!s}'.format(
                look_up_dict[mode_str.upper()]
            )
        )

        self.raise_errors()
        return self.get_mode()

    def get_samp_rate(self):
        """ Get the sample rate of the pulse generator hardware

        :return float: The current sample rate of the device (in Hz)
        """

        return float(
            self.query('SOUR1:FREQ?')
        )

    def set_samp_rate(self, samp_rate):
        """ Set the sample rate of the pulse generator hardware.

        :param float samp_rate: The sampling rate to be set (in Hz)

        :return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """

        self.write('SOUR1:FREQ {} Hz'.format(samp_rate))
        self.query('*OPC?')

        self.raise_errors()
        return self.get_samp_rate()

    def get_analog_level(self):
        """ Retrieve the analog amplitude and offset of the provided channels.

        :return: nested dictionary:
                dict(
                    'a_ch1'={'amp_pp': amp_1, 'offset': offset_1},
                    'a_ch2'={'amp_pp': amp_2, 'offset': offset_2}
                )
                Outer keys (str)- the channel name (i.e. 'a_ch1' and 'a_ch2')
                Inner keys (str) - 'amp_pp' and 'offset'
                Items - the values for those channels.
                Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.
        """

        level_dict = dict()

        # Depending on included options, offset may not be available
        no_offset = ('02' in self.option_list) or ('06' in self.option_list)

        for ch_name in self._get_all_anlg_chs():
            ch_num = int(ch_name.rsplit('_ch', 1)[1])
            level_dict[ch_name] = dict()

            # Amplitude-PP
            level_dict[ch_name]['amp_pp'] = float(
                self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num))
            )

            # Offset
            level_dict[ch_name]['offset'] = 0.0 if no_offset else float(
                self.query('SOUR{0:d}:VOLT:OFFS?'.format(ch_num))
            )

        return level_dict

    def set_analog_level(self, level_dict):
        """ Set amplitude-pp and/or offset.

        :param level_dict: nested dictionary:
                dict(
                    'a_ch1'={'amp_pp': amp_1, 'offset': offset_1},
                    'a_ch2'={'amp_pp': amp_2, 'offset': offset_2}
                )
                Outer keys (str)- the channel number (i.e. 'a_ch1' and 'a_ch2')
                Inner keys (str) - 'amp_pp' and 'offset'
                Items - the values for those channels [in Volts].

                If some channels/parameters are not mentioned, they are not changed.

        :return: nested dict of the same structure as level_dict
        """

        for ch_name in level_dict.keys():
            ch_num = int(ch_name.rsplit('_ch', 1)[1])

            # set amplitude-pp
            if 'amp_pp' in level_dict[ch_name].keys():
                self.write(
                    'SOUR{}:VOLT:AMPL {}'.format(
                        ch_num,
                        level_dict[ch_name]['amp_pp']
                    )
                )
                # Block until the operation is complete
                self.query('*OPC?')

            # set offset
            if 'offset' in level_dict[ch_name].keys():
                self.write(
                    'SOUR{}:VOLT:OFFSET {}'.format(
                        ch_num,
                        level_dict[ch_name]['offset']
                    )
                )
                # Block until the operation is complete
                self.query('*OPC?')

        self.raise_errors()
        return self.get_analog_level()

    def get_digital_level(self):
        """ Retrieve the digital low and high level of all marker channels.

        :return dict:
                {
                    'd_ch1': {'low': 0.1, 'high': 1.2},
                    'd_ch2': {'low': 0.0, 'high': 1.0},
                    'd_ch3': {'low': 0.0, 'high': 1.0},
                    'd_ch4': {'low': 0.0, 'high': 1.0}

                }
        """

        level_dict = dict()

        for ch_name in self._get_all_dgtl_chs():
            level_dict[ch_name] = dict()
            d_ch_num = int(ch_name.rsplit('_ch', 1)[1])

            # Convert into 'Analog channel + marker number'
            a_ch_num = (d_ch_num + 1) // 2
            d_ch_num -= 2 * (a_ch_num - 1)

            # Low
            level_dict[ch_name]['low'] = float(
                self.query(
                    'SOUR{}:MARK{}:VOLT:LOW?'.format(a_ch_num, d_ch_num)
                )
            )
            # High
            level_dict[ch_name]['high'] = float(
                self.query(
                    'SOUR{}:MARK{}:VOLT:HIGH?'.format(a_ch_num, d_ch_num)
                )
            )

        return level_dict

    def set_digital_level(self, level_dict):
        """ Set low/high value of marker channels.

        :param level_dict: nested dict of the following structure:
            {
                    'd_ch1': {'low': 0.1, 'high': 1.2},
                    'd_ch2': {'low': 0.0, 'high': 1.0},
                    'd_ch3': {'low': 0.0, 'high': 1.0},
                    'd_ch4': {'low': 0.0, 'high': 1.0}

            }
        If some channels/markers/values are not mentioned, corresponding values
        are not changed.

        :return dict: the actual levels.
        """

        # Determine the requested final state:
        #   get current state
        req_dict = self.get_digital_level()
        #   update it with the new values from level_dict
        for d_ch_name in level_dict.keys():
            try:
                if 'low' in level_dict[d_ch_name]:
                    req_dict[d_ch_name]['low'] = level_dict[d_ch_name]['low']

                if 'high' in level_dict[d_ch_name]:
                    req_dict[d_ch_name]['high'] = level_dict[d_ch_name]['high']

            except KeyError:
                msg_str = 'set_digital_level(): channel {} is not available. \n' \
                          'Currently available digital channels: \n' \
                          '     {}'.format(d_ch_name, self._get_all_dgtl_chs())

                self.log.exception(msg_str=msg_str)
                raise PGenError(msg_str)

        # Set all values
        for d_ch_name in req_dict.keys():
            d_ch_num = int(d_ch_name.rsplit('_ch', 1)[1])

            # Convert into 'Analog channel + marker number'
            a_ch_num = (d_ch_num + 1) // 2
            d_ch_num -= 2 * (a_ch_num - 1)

            # Low
            self.write(
                'SOUR{}:MARK{}:VOLT:LOW {}'.format(
                    a_ch_num,
                    d_ch_num,
                    req_dict[d_ch_name]['low']
                )
            )
            self.query('*OPC?')

            # High
            self.write(
                'SOUR{}:MARK{}:VOLT:HIGH {}'.format(
                    a_ch_num,
                    d_ch_num,
                    req_dict[d_ch_name]['high']
                )
            )
            self.query('*OPC?')

        # Check if the operation was successful
        #   - check for explicit error messages
        self.raise_errors()

        #   - check if the actual set values coincide with requested:
        #     if the requested values do not satisfy hardware restrictions,
        #     device will try to adjust previously set value [low] when setting
        #     the next one [high]. This may mask the error: no explicit exception
        #     will be produced, but the actual values will be different from expected.
        actual_dict = self.get_digital_level()
        if req_dict != actual_dict:
            msg_str = 'set_digital_level(): the actual set value is different fro expected: \n' \
                      'requested = {} \n' \
                      '   actual = {} \n' \
                      'Most probably the requested values do not satisfy hardware restrictions ' \
                      'on min/max amplitude [high-low] or overall voltage window.' \
                      ''.format(req_dict, actual_dict)

            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        return self.get_digital_level()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        :return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """

        if self._has_interleave():
            return bool(int(
                self.query('AWGC:INT:STAT?')
            ))
        else:
            return False

    def set_interleave(self, state):
        """ Turns the interleave of an AWG on or off.

        :param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        :return bool: actual interleave status (True: ON, False: OFF)
        """

        if self._has_interleave():
            self.write(
                'AWGC:INT:STAT {}'.format(int(state))
            )
            self.query('*OPC?')
            # Error check
            self.raise_errors()

        # Enable all markers for all active analog channels
        # (set DAC resolution to 8)
        # FIXME: implement more generic (devices with 14-bit DAC)

        for a_ch_name in self._get_all_anlg_chs():
            a_ch_num = int(a_ch_name.rsplit('_ch', 1)[1])
            self.write(
                'SOUR{}:DAC:RES {}'.format(
                    a_ch_num,
                    8
                )
            )
            self.query('*OPC?')
            # Error check
            self.raise_errors()

        return self.get_interleave()

    def set_lowpass_filter(self, ch_num, cutoff_freq):
        """ Set a lowpass filter to the analog channels of the AWG.

        :param int ch_num: To which channel to apply, either 1 or 2.
        :param cutoff_freq: Cutoff Frequency of the lowpass filter in Hz.

        :return: (int) success code 0. Exception is produced in the case of error.
        """

        # Low-pass filter is not available on instruments with options 02 and 06
        if '02' in self.option_list or '06' in self.option_list:
            msg_str = 'set_lowpass_filter(): low-pass filter is not available for options [02] and [06].'
            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        self.write(
            'OUTPUT{}:FILTER:LPASS:FREQUENCY {}'
            ''.format(ch_num, cutoff_freq)
        )
        self.query('*OPC?')

        self.raise_errors()
        return 0

    #  Technical methods

    def _get_all_chs(self):
        """Helper method to return a sorted list of all technically available
        channel numbers (e.g. ['a_ch1', 'a_ch2', 'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4'])

        :return list: Sorted list of channel numbers
        """

        # Determine number of available channels based on model
        if self.model == 'AWG7122C':
            available_chs = ['a_ch1', 'd_ch1', 'd_ch2']

            if not self.get_interleave():
                available_chs.extend(['a_ch2', 'd_ch3', 'd_ch4'])

        else:
            msg_str = 'Failed to determine number of available channels: \n' \
                      'number of channels is not specified for "{}" model. ' \
                      'Add this model to _get_all_chs()' \
                      ''.format(self.model)
            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        return sorted(available_chs)

    def _get_all_anlg_chs(self):
        """
        Helper method to return a sorted list of all technically available analog channel
        descriptors (e.g. ['a_ch1', 'a_ch2'])

        :return list: Sorted list of analog channels
        """

        return sorted(
            ch for ch in self._get_all_chs() if ch.startswith('a')
        )

    def _get_all_dgtl_chs(self):
        """
        Helper method to return a sorted list of all technically available digital channel
        descriptors (e.g. ['d_ch1', 'd_ch2'])

        :return list: Sorted list of digital channels
        """

        return sorted(
            ch for ch in self._get_all_chs() if ch.startswith('d')
        )

    @staticmethod
    def _is_digital(ch_name):
        if 'd' in ch_name:
            return True
        else:
            return False

    def _zeroing_enabled(self):
        """
        Checks if the zeroing option is enabled. Only available on devices with option '06'.

        @return bool: True: enabled, False: disabled
        """
        if self._has_interleave():
            return bool(int(self.query('AWGC:INT:ZER?')))
        return False

    def _has_interleave(self):
        """ Check if the device has the interleave option installed

            :return bool: device has interleave option
        """

        return '06' in self.option_list

    # =========================================================================
    # Waveform and Sequence generation methods
    # =========================================================================

    # ================ Waveform ================

    def write_wfm(self, pb_obj, len_min=1, len_max=float('inf'), len_step=1, step_adj=False):

        pb_obj = copy.deepcopy(pb_obj)

        req_ch_set = set(pb_obj.p_dict.keys())
        avail_ch_set = set(self._get_all_chs())

        # Sanity check: all requested channels are available
        if not req_ch_set.issubset(avail_ch_set):
            msg_str = 'write_wfm(): the following channels of the PulseBlock are not available: \n' \
                      '{} \n' \
                      ''.format(sorted(list(req_ch_set - avail_ch_set)))

            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        # All available channels have to have a waveform assigned.
        # If some channels are not used in the pb_obj,
        # fill them with default value pulses
        miss_ch_set = avail_ch_set - req_ch_set
        for miss_ch_name in miss_ch_set:
            if self._is_digital(miss_ch_name):
                pb_obj.dflt_dict[miss_ch_name] = po.DFalse()
            else:
                pb_obj.dflt_dict[miss_ch_name] = po.DConst(val=0.0)

        # Sample pulse block
        samp_dict, n_samp_pts, add_samp_pts = pb_sample(
            pb_obj=pb_obj,
            samp_rate=self.get_samp_rate(),
            len_min=len_min,
            len_max=len_max,
            len_step=len_step,
            len_adj=step_adj,
            debug=False
        )

        # Write waveforms. One for each analog channel.
        for a_ch_name in self._get_all_anlg_chs():
            # Get the integer analog channel number
            a_ch_num = int(a_ch_name.rsplit('ch', 1)[1])
            # Get the digital channel specifiers belonging to this analog channel markers
            mrk_ch_1 = 'd_ch{0:d}'.format(a_ch_num * 2 - 1)
            mrk_ch_2 = 'd_ch{0:d}'.format(a_ch_num * 2)

            start_t = time.time()
            # Encode marker information in an array of bytes (uint8). Avoid intermediate copies!!!
            mrk_bytes = samp_dict[mrk_ch_2].view('uint8')
            tmp_bytes = samp_dict[mrk_ch_1].view('uint8')
            # Marker bits live in the LSB of the byte, as opposed to the AWG70k
            np.left_shift(mrk_bytes, 1, out=mrk_bytes)
            np.left_shift(tmp_bytes, 0, out=tmp_bytes)
            np.add(mrk_bytes, tmp_bytes, out=mrk_bytes)
            self.log.debug('Prepared digital channel data: {0}'.format(time.time() - start_t))

            # Create waveform name string
            file_name = '{0}_ch{1:d}'.format(pb_obj.name, a_ch_num)

            # Write WFM to a file on local HDD
            start = time.time()
            self._write_wfm_file(
                filename=file_name,
                anlg_samp_list=samp_dict[a_ch_name],  # FIXME: compensate for incorrect amplitude
                mrk_byte_list=mrk_bytes
            )
            self.log.debug('Wrote WFM file to local HDD: {0}'.format(time.time() - start))

            # Send file to AWG over FTP and load into workspace
            start = time.time()
            self._send_file(filename=file_name + '.wfm')
            self.log.debug('Sent WFM file to AWG HDD: {0}'.format(time.time() - start))

            # Load waveform to the AWG fast memory (waveform will appear in "User Defined" list)
            start = time.time()
            self.write('MMEM:IMP "{0}","{1}",WFM'.format(file_name, file_name + '.wfm'))

            # Wait for everything to complete
            self.query('*OPC?')

            # Just to make sure
            while file_name not in self.get_waveform_names():
                time.sleep(0.2)
            self.log.debug('Loaded WFM file into workspace: {0}'.format(time.time() - start))

        self.raise_errors()

        return samp_dict#0

    def load_waveform(self, load_dict):
        """ Loads a wfm_name to the specified channel of AWG.

        :param load_dict: a dictionary with keys being one of the channel number
                          and values being the name of the already written wfm_name to
                          load into the channel.
                          Examples:   {1: 'rabi_ch1', 2: 'rabi_ch2'}

        :return dict: Dictionary containing the actually loaded waveforms per channel.
        """

        # Load waveforms into channels
        for ch_num, wfm_name in load_dict.items():

            # load into channel
            self.write('SOUR{0:d}:WAV "{1}"'.format(ch_num, wfm_name))

            self.query('*OPC?')
            while self.query('SOUR{0:d}:WAV?'.format(ch_num)) != wfm_name:
                time.sleep(0.1)

        # self.set_mode('C')
        return self.get_loaded_assets()

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        wfm_list_len = int(self.query('WLIS:SIZE?'))
        wfm_list = list()
        for index in range(wfm_list_len):
            wfm_list.append(self.query('WLIS:NAME? {0:d}'.format(index)))
        return sorted(wfm_list)

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory (from "User Defined" list).

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        if isinstance(waveform_name, str):
            waveform_name = [waveform_name]

        avail_waveforms = self.get_waveform_names()
        deleted_waveforms = list()
        for waveform in waveform_name:
            if waveform in avail_waveforms:
                self.write('WLIS:WAV:DEL "{0}"'.format(waveform))
                deleted_waveforms.append(waveform)
        return sorted(deleted_waveforms)

    # ======== Wfm Technical ========

    def _write_wfm_file(self, filename, anlg_samp_list, mrk_byte_list):
        """
        Appends a sampled chunk of a whole waveform to a wfm-file. Create the file
        if it is the first chunk.
        If both flags (is_first_chunk, is_last_chunk) are set to TRUE it means
        that the whole ensemble is written as a whole in one big chunk.

        @param filename: string, represents the name of the sampled waveform
        @param anlg_samp_list: dict containing float32 numpy ndarrays, contains the
                                       samples for the analog channels that
                                       are to be written by this function call.
        @param mrk_byte_list: np.ndarray containing bool numpy ndarrays, contains the samples
                                      for the digital channels that
                                      are to be written by this function call.
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known in advance.
        """

        total_samp_num = len(anlg_samp_list)

        # Max number of bytes to write in one command
        max_chunk_bytes = 104857600  # 100 MB
        # respective number of analog samples
        # [analog sample (float32) - 4 bytes, markers sample - 1 byte]
        samp_chunk_size = min(
            max_chunk_bytes // 5,
            total_samp_num
        )

        # Create the WFM file.
        if not filename.endswith('.wfm'):
            filename += '.wfm'
        wfm_path = os.path.join(self._local_wfm_dir, filename)

        #   - write header
        with open(wfm_path, 'wb') as wfm_file:
            num_bytes = str(total_samp_num * 5)
            num_digits = str(len(num_bytes))
            header = 'MAGIC 1000\r\n#{0}{1}'.format(num_digits, num_bytes)
            wfm_file.write(header.encode())

        # Combine analog (float32) and digital (uint8) values into a single 5-bytes sample
        write_array = np.zeros(samp_chunk_size, dtype='float32, uint8')

        # Consecutively prepare and write chunks of maximal size max_chunk_bytes to file
        samps_written = 0
        with open(wfm_path, 'ab') as wfm_file:
            while samps_written < total_samp_num:
                write_end = samps_written + samp_chunk_size
                # Prepare tmp write array
                write_array['f0'] = anlg_samp_list[samps_written:write_end]
                write_array['f1'] = mrk_byte_list[samps_written:write_end]
                # Write to file
                wfm_file.write(write_array)
                # Increment write counter
                samps_written = write_end
                # Reduce write array size if
                if 0 < total_samp_num - samps_written < samp_chunk_size:
                    write_array.resize(total_samp_num - samps_written)

        del write_array

        # Append the footer: the sample rate, which was used for that file
        footer = 'CLOCK {0:16.10E}\r\n'.format(self.get_samp_rate())
        with open(wfm_path, 'ab') as wfm_file:
            wfm_file.write(footer.encode())

        return 0

    def _send_file(self, filename):
        """

        @param filename:
        @return:
        """

        filepath = os.path.join(self._local_wfm_dir, filename)

        # Sanity check: file is present
        if not os.path.isfile(filepath):
            msg_str = '_send_file: No file "{0}" found in "{1}". Unable to send!'\
                      ''.format(filename, self._local_wfm_dir)
            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        # Delete old file on AWG by the same filename
        self._delete_file(filename)

        # Transfer file
        with FTP(self._ftp_ip_str) as ftp:
            ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
            ftp.cwd(self._remote_wfm_dir)
            with open(filepath, 'rb') as file:  # In this case "file" refers to the file on user's PC
                ftp.storbinary('STOR ' + filename, file)

        return 0

    def _get_filenames_on_device(self):
        """

        @return list: filenames found in <ftproot>\\waves
        """

        filename_list = list()
        with FTP(self._ftp_ip_str) as ftp:
            ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
            ftp.cwd(self._remote_wfm_dir)
            # get only the files from the dir and skip possible directories
            log = list()
            ftp.retrlines('LIST', callback=log.append)
            for line in log:
                if '<DIR>' not in line:
                    # that is how a potential line is looking like:
                    #   '05-10-16  05:22PM                  292 SSR aom adjusted.seq'
                    # The first part consists of the date information. Remove this information and
                    # separate the first number, which indicates the size of the file. This is
                    # necessary if the filename contains whitespaces.
                    size_filename = line[18:].lstrip()
                    # split after the first appearing whitespace and take the rest as filename.
                    # Remove for safety all trailing and leading whitespaces:
                    filename = size_filename.split(' ', 1)[1].strip()
                    filename_list.append(filename)
        return filename_list

    def _delete_file(self, filename):
        """

        @param str filename: The full filename to delete from FTP cwd
        """

        if filename in self._get_filenames_on_device():
            with FTP(self._ftp_ip_str) as ftp:
                ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
                ftp.cwd(self._remote_wfm_dir)
                ftp.delete(filename)
        return 0

    # ================ Sequence ================

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param name: str, the name of the waveform to be created/append to
        @param sequence_parameters: list, contains the parameters for each sequence step and
                                        the according waveform names.

        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        sequence_parameter_list = sequence_parameters  # introduce new name to append _list suffix for clarity

        # Check if device has sequencer option installed
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation is not possible on this AWG: sequencer option is not installed.')
            return -1
        # Give a warning if run mode is nor Sequence
        run_mode = self.get_mode()
        if run_mode != 'S':
            self.log.warn('set_sequence_jump_mode(): current run mode "{}" is not Sequence'.format(run_mode))

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameter_list:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in device memory.'.format(name, waveform_tuple))
                return -1

        # Create list of active analog channel numbers for further sanity check
        ch_state_dict = self.get_active_channels()
        active_a_ch_list = sorted(
            chnl for chnl in ch_state_dict if chnl.startswith('a') and ch_state_dict[chnl]
        )
        active_a_ch_num_list = sorted(
            int(chnl.rsplit('_ch', 1)[1]) for chnl in active_a_ch_list
        )

        # In essence, a sequence is just a table which references already loaded waveforms and specifies repetitions,
        # wait for trigger, GoTo, and JumpTo.
        #
        # Only one pulse sequence can be stored in AWG's memory, and it is not possible to load it from file,
        # so there is no need for sequence name.
        #
        # To create a new pulse sequence, one needs to set the length to the expected number of sequence elements.
        # This will fill the table with default lines, which are to be filled later with actual settings.
        # If there are already some lines in the table, and self.write('SEQ:LENG 0') sets length which exceeds
        # current table length, the existing entries stay unchanged and the new empty lines are added.
        # If the operation sets smaller length, the corresponig lines at the bottom are erased.

        # Erase the AWG's sequence table
        self.write('SEQ:LENG 0')
        # Create empty lines in the sequence table
        num_elements = len(sequence_parameter_list)
        self.write('SEQ:LENG {0:d}'.format(num_elements))

        # Fill in sequence information for each sequence element (that is, for each table line)
        for elem_num, (elem_wfm_tuple, elem_param_dict) in enumerate(sequence_parameter_list, 1):

            # Sanity check: set of active channels should coincide with the set of waveforms passed for this element
            wfm_ch_num_list = sorted(
                int(wfm_name.rsplit('_ch', 1)[1]) for wfm_name in elem_wfm_tuple
            )
            if active_a_ch_num_list != wfm_ch_num_list:
                self.log.error('write_sequence(), sequence element #{0:d}:\n'
                               'the set of active channels: {1}\n'
                               'does not match \n'
                               'requested set of waveforms: {2}\n'
                               'write_sequence() was aborted'
                               ''.format(elem_num, active_a_ch_list, sorted(elem_wfm_tuple)))
                return -1

            # Set waveforms to all analog channels given
            for wfm_name in elem_wfm_tuple:
                chnl_num = int(wfm_name.rsplit('_ch', 1)[1])
                self.sequence_set_waveform(wfm_name, elem_num, chnl_num)

            # Set all other applicable fields of the table row.
            # There are 3 possible cases, different in which fields are available:
            #   - subsequence: Wait, GoTo, and Event_Jump_To are not available
            #   - sequence Dynamic Jump mode: Event_Jump_To is not available
            #   - sequence Event Jump mode: all settings are available

            # @param bool is_subsequence:
            # @param jump_mode: str {'EJUMP'|'DJUMP'}, select between Event-jump or Dynamic-jump mode
            is_subsequence = False
            jump_mode = 'EJUM'

            # Set "Repetitions", available in all cases
            self.sequence_set_repetitions(elem_num, elem_param_dict['repetitions'])

            if not is_subsequence:
                # Set "Wait for trigger", not available for subsequence
                self.sequence_set_wait_trigger(elem_num, elem_param_dict['wait_for'])
                # Set "go_to" parameter, not available for subsequence
                self.sequence_set_goto(elem_num, elem_param_dict['go_to'])

                if jump_mode == 'EJUM':
                    # Set "Event_Jump_To", available only in the Event_Jump mode
                    self.sequence_set_event_jump(elem_num, elem_param_dict['event_jump_to'])

        # Wait for everything to complete
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)

        # Set flag states
        self._written_seqs = [name]

        self.raise_errors(level='warn')

        return num_elements

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param sequence_name:  dict|list, a dictionary with keys being one of the available channel
                                      index and values being the name of the already written
                                      waveform to load into the channel.
                                      Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                  {1: rabi_ch2, 2: rabi_ch1}
                                      If just a list of waveform names if given, the channel
                                      association will be invoked from the channel
                                      suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        # FIXME: Is this check necessary?
        if sequence_name not in self.get_sequence_names():
            self.log.error('Unable to load sequence.\n'
                           'Sequence to load is missing on device memory.')
            return self.get_loaded_assets()

        # set the AWG to Sequence Run Mode:
        self.set_mode('S')
        # set the AWG to the proper jump mode:
        # FIXME: extend to include Dynamic jump mode
        self.set_sequence_jump_mode(jump_mode='EJUM')

        self._loaded_seqs = [sequence_name]
        return self.get_loaded_assets()

    def set_sequence_jump_mode(self, jump_mode):
        """
        Set sequencer to proper jump mode

        :param jump_mode: str, sequence jump mode.
                            Valid values:
                                'EJUM' - Event Jump
                                'DJUM' - Dynamic Jump
        :return: error code: int
                            0 -- Ok
                            -1 -- Error
        """

        # Sanity checks
        if not self.has_sequence_mode():
            self.log.error('Sequence generation is not possible: sequencer option is not installed on this AWG.')
            return -1

        # Set jump mode
        if jump_mode == 'EJUM':
            self.write('AWGControl:EVENt:JMODe EJUMP')
        elif jump_mode == 'DJUM':
            self.write('AWGControl:EVENt:JMODe DJUMP')
        else:
            self.log.error('set_sequence_jump_mode(): invalid argument passed: {}\n'
                           'Valid values are: "EJUM" - Event_Jump and "DJUM" - Dynamic_Jump'.format(jump_mode))
            return -1

        # Check that the jump mode was successfully set
        actual_mode = self.query('AWGControl:EVENt:JMODe?')
        if actual_mode != jump_mode:
            self.log.error('set_sequence_jump_mode(): failed to set sequence jump mode\n'
                           'requested mode: {0}\n'
                           ' obtained mode: {1}\n'.format(jump_mode, actual_mode))
            return -1

        return 0

    def get_sequence_jump_mode(self):
        """
        Returns current Sequencer Jump mode
        :return: str, 'EJUM' - Event Jump
                      'DJUM' - Dynamic Jump
        """

        if not self.has_sequence_mode():
            self.log.error('Sequence generation is not possible: sequencer option is not installed on this AWG.')
            return -1

        return self.query('AWGControl:EVENt:JMODe?')

    def sequence_set_waveform(self, wfm_name, elem_num, chnl_num):
        """
        Set the waveform 'wfm_name' to channel 'chnl_num' at table raw 'elem_num'.

        @param str wfm_name: Name of the waveform which should be added from the AWG's memory
        @param int elem_num: element number to be edited (line number in the sequence table)
        @param int chnl_num: analog channel number, to which the waveform should be assigned

        @return int: error code
        """
        if not self.has_sequence_mode():
            self.log.error('Sequence generation is not possible: sequencer option is not installed on this AWG.')
            return -1

        self.write('SEQ:ELEM{0:d}:WAV{1} "{2}"'.format(elem_num, chnl_num, wfm_name))

        self.raise_errors(level='warn')
        return 0

    def sequence_set_repetitions(self, elem_num, repeat=1):
        """
        Set the repetition counter at sequence element "elem_num" to "repeat" times.
        A repeat value of -1 denotes infinite repetitions; 0 and 1 both mean the step is played once.

        @param int elem_num: Sequence step to be edited
        @param int repeat: number of repetitions. (-1: infinite; 0 and 1 : once; 2: twice, ...)

        @return int: error code
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1
        if repeat < 0:
            self.write('SEQ:ELEM{0:d}:LOOP:INFINITE ON'.format(elem_num))
        else:
            if repeat == 0:
                repeat = 1
            self.write('SEQ:ELEM{0:d}:LOOP:INFINITE OFF'.format(elem_num))
            self.write('SEQ:ELEM{0:d}:LOOP:COUNT {1:d}'.format(elem_num, repeat))

        self.raise_errors(level='warn')
        return 0

    def sequence_set_goto(self, elem_num, goto=-1):
        """

        @param int elem_num: Sequence step to be edited
        @param int goto: positive integer - number of sequence element to go to after completing palying elem_num,
                         negative integer and 0 - disable GoTo

        @return int: error code: 0 -- Ok, -1 -- Error
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        if goto > 0:
            goto = str(int(goto))
            self.write('SEQ:ELEM{0:d}:GOTO:STATE ON'.format(elem_num))
            self.write('SEQ:ELEM{0:d}:GOTO:INDEX {1}'.format(elem_num, goto))
        else:
            self.write('SEQ:ELEM{0:d}:GOTO:STATE OFF'.format(elem_num))

        self.raise_errors(level='warn')
        return 0

    def sequence_set_event_jump(self, elem_num, jump_to=-1):
        """
        Set the event trigger input of the specified sequence step and the jump_to destination.

        @param int elem_num: Sequence step to be edited
        @param int jump_to: The sequence step to jump to. 0 is interpreted as next step. -1 is interpreted as OFF

        @return int: error code
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        # Set event_jump_to (works even when jump mode is set to Dynamic Jump)
        if jump_to > 0:
            self.write('SEQ:ELEM{0:d}:JTAR:TYPE INDEX'.format(elem_num))
            self.write('SEQ:ELEM{0:d}:JTAR:INDEX {1}'.format(elem_num, jump_to))
        elif jump_to == 0:
            self.write('SEQ:ELEM{0:d}:JTAR:TYPE NEXT'.format(elem_num))
        elif jump_to == -1:
            self.write('SEQ:ELEM{0:d}:JTAR:TYPE OFF'.format(elem_num))
        else:
            self.log.error('sequence_set_event_jump(): invalid value of jump_to: {}'.format(jump_to))
            return -1

        self.raise_errors(level='warn')
        return 0

    def sequence_set_wait_trigger(self, elem_num, trigger='OFF'):
        """
        Make a certain sequence step wait for a trigger to start playing.

        @param int elem_num: Sequence step to be edited
        @param str trigger: Trigger string specifier. Valid values: {'OFF', 'ON'}

        @return int: error code
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        if '08' not in self.option_list:
            self.log.warn('sequence_set_wait_trigger(): The instrument without option 08 always sets Wait Trigger On.\n'
                          'Trying to set the wait trigger state to off in an instrument without option 08 '
                          'will cause an error')

        trigger_val = self._event_triggers.get(trigger)
        if trigger_val is None:
            self.log.error('Invalid trigger specifier "{0}".\n'
                           'Please choose one of: "OFF", "ON"'.format(trigger))
            return -1

        if trigger_val != 'OFF':
            self.write('SEQ:ELEM{0:d}:TWAIT ON'.format(elem_num))
        else:
            self.write('SEQ:ELEM{0:d}:TWAIT OFF'.format(elem_num))

        self.raise_errors(level='warn')
        return 0

    def set_jump_timing(self, synchronous=False):
        """Sets control of the jump timing in the AWG.

        @param bool synchronous: if True the jump timing will be set to synchornous, otherwise the
                                 jump timing will be set to asynchronous.

        If the Jump timing is set to asynchornous the jump occurs as quickly as possible after an
        event occurs (e.g. event jump tigger), if set to synchornous the jump is made after the
        current waveform is output. The default value is asynchornous.
        """
        timing = 'SYNC' if synchronous else 'ASYN'
        self.write('EVEN:JTIM {0}'.format(timing))

        self.raise_errors(level='warn')

    def make_sequence_continuous(self):
        """
        Usually after a run of a sequence the output stops. Many times it is desired that the full
        sequence is repeated many times. This is achieved here by setting the 'jump to' value of
        the last element to 'First'

        @return int last_step: The step number which 'jump to' has to be set to 'First'
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        last_step = int(self.query('SEQ:LENG?'))
        err = self.sequence_set_goto(last_step, 1)
        if err < 0:
            last_step = err
        return last_step

    def force_jump_sequence(self, target):
        """
        This command forces the sequencer to jump to the specified sequnce step. A
        force jump does not require a trigger event to execute the jump.

        @param target: Step to jump to. Possible options are:
            <NR1> - This forces the sequencer to jump to the specified step, where the
            value is between 1 and 16000.

        """
        # FIXME: Doesn't work properly!!!
        # FIXME: AWG7122C error: 5000 "Sequence/Waveform loading error; E11200 - SEQUENCE:JUMP:IMMEDIATE 2
        # FIXME: AWG7122C error: -221 "Settings conflict; E11307 - SEQUENCE:JUMP:IMMEDIATE 1

        self.write('SEQUENCE:JUMP:IMMEDIATE {0}'.format(target))

        self.raise_errors(level='warn')

        return

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """

        return self._written_seqs

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        self.write('SEQUENCE:LENGTH 0')
        return list()

    def get_sequencer_mode(self, output_as_int=False):
        """ Asks the AWG which sequencer mode it is using.

        @param: bool output_as_int: optional boolean variable to set the output
        @return: str or int with the following meaning:
                'HARD' or 0 indicates Hardware Mode
                'SOFT' or 1 indicates Software Mode
                'Error' or -1 indicates a failure of request

        It can be either in Hardware Mode or in Software Mode. The optional
        variable output_as_int sets if the returned value should be either an
        integer number or string.
        """
        if self.has_sequence_mode():
            message = self.query('AWGC:SEQ:TYPE?')
            if 'HARD' in message:
                return 0 if output_as_int else 'Hardware-Sequencer'
            elif 'SOFT' in message:
                return 1 if output_as_int else 'Software-Sequencer'
        return -1 if output_as_int else 'Request-Error'

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        if '08' in self.option_list:
            return True
        return False

    # ================ Wfm and Seq common Technical ================

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """

        # Get all active analog channels
        a_ch_name_list = self._get_all_anlg_chs()
        a_ch_num_list = sorted(
            int(ch_name.split('_ch')[1]) for ch_name in a_ch_name_list
        )

        # Get assets per channel
        loaded_assets = dict()

        run_mode = self.query('AWGC:RMOD?')
        if run_mode in ['CONT', 'TRIG', 'GAT']:
            current_type = 'waveform'
            for ch_num in a_ch_num_list:
                loaded_assets[ch_num] = self.query('SOUR{0}:WAV?'.format(ch_num))
        elif run_mode == 'SEQ':
            current_type = 'sequence'
            for ch_num in a_ch_num_list:
                if len(self._loaded_seqs) > 0:
                    loaded_assets[ch_num] = self._loaded_seqs[0]
        else:
            msg_str = 'get_loaded_assets(): received unknown run mode: {}'\
                      ''.format(run_mode)
            self.log.error(msg_str=msg_str)
            raise PGenError(msg_str)

        return loaded_assets, current_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.
        (from "User Defined" list)

        @return int: error code (0:OK, -1:error)
        """

        self.write('WLIS:WAV:DEL ALL')
        if '09' in self.option_list:
            self.write('SLIS:SUBS:DEL ALL')

        self.write('SEQUENCE:LENGTH 0')
        self._written_seqs = []
        self._loaded_seqs = []

        self.raise_errors()

        return 0

    # def get_constraints(self):
    #     """
    #     Retrieve the hardware constrains from the Pulsing device.
    #
    #     @return constraints object: object with pulser constraints as attributes.
    #
    #     Provides all the constraints (e.g. sample_rate, amplitude, total_length_bins,
    #     channel_config, ...) related to the pulse generator hardware to the caller.
    #
    #         SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE CONSTRAINTS!!!
    #
    #     If you are not sure about the meaning, look in other hardware files to get an impression.
    #     If still additional constraints are needed, then they have to be added to the
    #     PulserConstraints class.
    #
    #     Each scalar parameter is an ScalarConstraints object defined in cor.util.interfaces.
    #     Essentially it contains min/max values as well as min step size, default value and unit of
    #     the parameter.
    #
    #     PulserConstraints.activation_config differs, since it contain the channel
    #     configuration/activation information of the form:
    #         {<descriptor_str>: <channel_set>,
    #          <descriptor_str>: <channel_set>,
    #          ...}
    #
    #     If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
    #     sequence mode) just leave it out so that the default is used (only zeros).
    #     """
    #
    #     # TODO: Check values for AWG7122c
    #     constraints = PulserConstraints()
    #
    #     constraints.waveform_length.min = 1
    #     constraints.waveform_length.step = 4
    #     constraints.waveform_length.default = 80
    #     if '01' in self.option_list:
    #         constraints.waveform_length.max = 64800000
    #     else:
    #         constraints.waveform_length.max = 32400000
    #
    #     constraints.waveform_num.min = 1
    #     constraints.waveform_num.max = 32000
    #     constraints.waveform_num.step = 1
    #     constraints.waveform_num.default = 1
    #
    #     constraints.sequence_num.min = 1
    #     constraints.sequence_num.max = 16000
    #     constraints.sequence_num.step = 1
    #     constraints.sequence_num.default = 1
    #
    #     constraints.subsequence_num.min = 1
    #     constraints.subsequence_num.max = 8000
    #     constraints.subsequence_num.step = 1
    #     constraints.subsequence_num.default = 1
    #
    #     # If sequencer mode is available then these should be specified
    #     constraints.repetitions.min = 0
    #     constraints.repetitions.max = 65539
    #     constraints.repetitions.step = 1
    #     constraints.repetitions.default = 0
    #
    #     # Device has only one trigger and no flags
    #     constraints.event_triggers = ['ON']
    #     constraints.flags = list()
    #
    #     constraints.sequence_steps.min = 0
    #     constraints.sequence_steps.max = 8000
    #     constraints.sequence_steps.step = 1
    #     constraints.sequence_steps.default = 0
    #
    #     return constraints



