# """ Broken due to dependency on pulseblock. Should be fixed once pulseblock is integrated"""

# from pylabnet.utils.logging.logger import LogHandler
# from pylabnet.hardware.interface.simple_p_gen import PGenError
# import pulseblock.pulse as po
# from pulseblock.pb_sample import pb_sample
# from pulseblock.pb_zip import pb_zip

# import os
# import time
# import visa
# import numpy as np
# from ftplib import FTP
# import copy

# from pylabnet.network.core.service_base import ServiceBase
# from pylabnet.network.core.client_base import ClientBase


# class Driver:
#     """ A hardware module for the Tektronix AWG7000 series for generating
#     waveforms and sequences thereof.

#     Adapted from github.com/Ulm-IQO/qudi.
#     """

#     def __init__(self,
#                  visa_adr_str, ftp_ip_str,
#                  ftp_username=None, ftp_pswrd=None,
#                  local_wfm_dir='user\\local_wfm_dir',
#                  remote_wfm_dir='remote_wfm_dir',
#                  visa_timeout=20,
#                  logger=None):

#         self.log = LogHandler(logger=logger)

#         # Declaration of internal variables -----------------------------------

#         self._awg = None  # This variable will hold a reference to the awg visa resource

#         self.option_list = list()  # will hold the encoded installed options available on _awg
#         self.model = None
#         self._local_wfm_dir = None
#         self._ftp_ip_str = None
#         self._ftp_username = None
#         self._ftp_pswrd = None
#         self._written_seqs = []  # Helper variable since written sequences can not be queried
#         self._loaded_seqs = []  # Helper variable since a loaded sequence can not be queried :(

#         # VISA connection -----------------------------------------------------

#         self._rm = visa.ResourceManager()
#         try:
#             self._awg = self._rm.open_resource(visa_adr_str)
#             # set timeout (in ms)
#             self._awg.timeout = visa_timeout * 1000
#             # Reset hardware
#             self.reset()
#         except:
#             self._awg = None

#             msg_str = 'VISA connection to address {} failed'.format(visa_adr_str)

#             self.log.exception(msg_str=msg_str)
#             raise PGenError(msg_str)

#         # FTP connection ------------------------------------------------------

#         # FTP (File Transfer Protocol) is used to transfer large waveform
#         # from PC's hard drive to AWG's hard drive:
#         #   - PulseBlock is sampled and the binary is stored in local_wfm_dir
#         #   - FTP transfers file to remote_wfm_dir on AWG's hard drive
#         #   - AWG loads the wfm into fast memory

#         self._ftp_ip_str = ftp_ip_str
#         self._ftp_username = ftp_username
#         self._ftp_pswrd = ftp_pswrd
#         self._remote_wfm_dir = remote_wfm_dir

#         # Test FTP connection and set current working dir to remote_wfm_dir
#         try:
#             with FTP(ftp_ip_str) as ftp:
#                 ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
#                 ftp.cwd(self._remote_wfm_dir)
#                 self.log.debug('FTP connection test. Working dir: {0}'.format(ftp.pwd()))
#         except:
#             msg_str = 'Attempt to establish FTP connection failed. \n' \
#                       'The following params where used: \n' \
#                       '     ftp_ip_str = {} \n' \
#                       '     ftp_username = {} \n' \
#                       '     ftp_pswrd = {} \n' \
#                       '     remote_wfm_dir = {}' \
#                       ''.format(ftp_ip_str, ftp_username, ftp_pswrd, remote_wfm_dir)

#             self.log.exception(msg_str=msg_str)
#             raise PGenError(msg_str)

#         # Create local_wfm_dir
#         if local_wfm_dir == 'user\\local_wfm_dir':
#             local_wfm_dir = os.path.expanduser('~\\local_wfm_dir')

#         if not os.path.exists(local_wfm_dir):
#             os.makedirs(os.path.abspath(local_wfm_dir))

#         self._local_wfm_dir = local_wfm_dir

#         # Determine device params ---------------------------------------------

#         # Get model and option list
#         mfg, self.model, ser, fw_ver = self.query('*IDN?').split(',')
#         self.option_list = self.query('*OPT?').split(',')
#         # Options of AWG7000 series:
#         #              Option 01: Memory expansion to 64,8 MSamples (Million points)
#         #              Option 06: Interleave and extended analog output bandwidth
#         #              Option 08: Fast sequence switching
#         #              Option 09: Subsequence and Table Jump

#         # Log confirmation info message ---------------------------------------
#         self.log.info(
#             'Found {} {} Serial: {} FW: {} \n'
#             'Installed options: {}'.format(
#                 mfg, self.model, ser, fw_ver, self.option_list
#             )
#         )

#     def close(self):
#         """ Deinitialisation performed during deactivation of the module.
#         """

#         # Closes the connection to the AWG
#         try:
#             self._awg.close()
#         except:
#             self.log.debug('Closing AWG connection using pyvisa failed.')

#         self.log.info('Closed connection to AWG')

#         return 0

#     # -------------------------------------------------------------------------
#     # Basic commands and Hardware settings
#     # -------------------------------------------------------------------------

#     # Basic commands

#     def write(self, cmd_str):
#         """ Sends a command string to the device.

#         Should only be used for non-responding (set-type) commands!
#         If the command is supposed to produce some response message,
#         use query() method.

#         @param string cmd_str: string containing the command
#         @return int: error code (0:OK, -1:error)
#         """

#         self._awg.write('*WAI')
#         bytes_written, status_code = self._awg.write(cmd_str)
#         # self._awg.write('*WAI')

#         # Block Python process until the operation is complete
#         # TODO: implement more robust blocking mechanism:
#         # TODO: to avoid timeout for very long operations
#         self._awg.query('*OPC?')

#         self.raise_errors()

#         return status_code

#     def query(self, question):
#         """ Query the device:
#             write request, read response, return formatted answer.

#         @param string question: string containing the command

#         @return string: the answer of the device to the 'question' in a string
#         """

#         try:
#             answer = self._awg.query(question)
#             answer = answer.strip()
#             answer = answer.rstrip('\n')
#             answer = answer.rstrip()
#             answer = answer.strip('"')
#             return answer

#         except Exception as exc_obj:
#             self.log.exception(msg_str='Exception in query()')

#             # If the reason for timeout is an incorrect command,
#             # raise_errors() should produce an exception.
#             self.raise_errors()
#             # This call is necessary to clean-up the error register
#             # such that subsequent commands do not break due to this
#             # error message still in the register.

#             # Else, some other error was produced.
#             # Just re-raise the original exception
#             raise exc_obj

#     def reset(self):
#         """ Reset the device.

#         @return int: error code (0:OK, -1:error)
#         """

#         self.write('*RST')

#         # Clear status register
#         self.write('*CLS')

#         return 0

#     def get_status(self):
#         """ Retrieves the status of the pulsing hardware

#         -1: 'Failed Request or Communication'
#          0: 'Device has stopped, but can receive commands'
#          1: 'Device is waiting for trigger'
#          2: 'Device is active and running'

#         @return (int, dict): inter value of the current status with the
#                              corresponding dictionary containing status
#                              description for all the possible status variables
#                              of the pulse generator hardware
#         """

#         current_status = -1 if self._awg is None else int(self.query('AWGC:RST?'))
#         return current_status

#     def start(self):
#         """ Switches the pulsing device on.

#         @return int: error code (0:OK, -1:error, higher number corresponds to
#                                  current status of the device. Check then the
#                                  class variable status_dic.)
#         """

#         # Switch outputs on
#         # (here it is assumed that all active analog channels have
#         # a waveform assigned, such that all active channels are switched on)
#         for ch in self._get_all_anlg_chs():
#             ch_num = int(ch.rsplit('_ch', 1)[1])
#             self.write(
#                 'OUTPUT{}:STATE ON'.format(ch_num)
#             )

#         # Start generator
#         self.write('AWGC:RUN')

#         return 0

#     def stop(self):
#         """ Switches the pulsing device off.

#         @return int: error code (0:OK, -1:error, higher number corresponds to
#                                  current status of the device. Check then the
#                                  class variable status_dic.)
#         """

#         self.write('AWGC:STOP')

#         for ch in self._get_all_anlg_chs():
#             ch_num = int(ch.rsplit('_ch', 1)[1])
#             self.write(
#                 'OUTPUT{0:d}:STATE OFF'.format(ch_num)
#             )

#         return 0

#     def raise_errors(self):
#         """Get all errors from the device and log them.

#         :return: (int) 0 is there is no errors.
#                  PGenError is produced in the case of error.
#         """

#         # Get all errors
#         read_next_err = True
#         has_error = False

#         msg_str_list = []

#         while read_next_err:
#             err = self.query('SYST:ERR?').split(',')

#             if int(err[0]) == 0:
#                 read_next_err = False
#             else:
#                 has_error = True
#                 msg_str_list.append(
#                     '{} {}'.format(err[0], err[1])
#                 )

#         # Log/raise if there are some errors
#         if has_error:

#             # Combine all error messages into a single string
#             # with one error per line
#             msg_str = '\n'.join(msg_str_list)

#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return 0

#     # Hardware settings

#     def get_mode(self):
#         """
#         Returns AWG run mode according to the following list:
#             continuous - 'C'
#             triggered  - 'T'
#             gated      - 'G'
#             sequence   - 'S'
#         @return str: 'C', 'T', 'G', 'S'.
#         """

#         run_mode_dict = {'CONT': 'C', 'TRIG': 'T', 'GAT': 'G', 'SEQ': 'S'}

#         answer = self.query('AWGC:RMOD?')
#         if answer in run_mode_dict:
#             return run_mode_dict[answer]
#         else:
#             msg_str = 'get_mode(): returned answer {} is not on the list of known run modes' \
#                       ''.format(answer)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#     def set_mode(self, mode_str):
#         """Change the run mode of the AWG7000 series.

#         :param str mode_str: Options for mode (case-insensitive):
#                             continuous - 'C'
#                             triggered  - 'T'
#                             gated      - 'G'
#                             sequence   - 'S'
#         """

#         look_up_dict = {
#             'C': 'CONT',
#             'T': 'TRIG',
#             'G': 'GAT',
#             'E': 'ENH',
#             'S': 'SEQ'
#         }
#         self.write(
#             'AWGC:RMOD {0!s}'.format(
#                 look_up_dict[mode_str.upper()]
#             )
#         )

#         return self.get_mode()

#     def get_samp_rate(self):
#         """ Get the sample rate of the pulse generator hardware

#         :return float: The current sample rate of the device (in Hz)
#         """

#         return float(
#             self.query('SOUR1:FREQ?')
#         )

#     def set_samp_rate(self, samp_rate):
#         """ Set the sample rate of the pulse generator hardware.

#         :param float samp_rate: The sampling rate to be set (in Hz)

#         :return float: the sample rate returned from the device (in Hz).

#         Note: After setting the sampling rate of the device, use the actually set return value for
#               further processing.
#         """

#         self.write('SOUR1:FREQ {} Hz'.format(samp_rate))

#         return self.get_samp_rate()

#     def get_analog_level(self):
#         """ Retrieve the analog amplitude and offset of the provided channels.

#         :return: nested dictionary:
#                 dict(
#                     'a_ch1'={'amp_pp': amp_1, 'offset': offset_1},
#                     'a_ch2'={'amp_pp': amp_2, 'offset': offset_2}
#                 )
#                 Outer keys (str)- the channel name (i.e. 'a_ch1' and 'a_ch2')
#                 Inner keys (str) - 'amp_pp' and 'offset'
#                 Items - the values for those channels.
#                 Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.
#         """

#         level_dict = dict()

#         # Depending on included options, offset may not be available
#         no_offset = ('02' in self.option_list) or ('06' in self.option_list)

#         for ch_name in self._get_all_anlg_chs():
#             ch_num = int(ch_name.rsplit('_ch', 1)[1])
#             level_dict[ch_name] = dict()

#             # Amplitude-PP
#             level_dict[ch_name]['amp_pp'] = float(
#                 self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num))
#             )

#             # Offset
#             level_dict[ch_name]['offset'] = 0.0 if no_offset else float(
#                 self.query('SOUR{0:d}:VOLT:OFFS?'.format(ch_num))
#             )

#         return level_dict

#     def set_analog_level(self, level_dict):
#         """ Set amplitude-pp and/or offset.

#         :param level_dict: nested dictionary:
#                 dict(
#                     'a_ch1'={'amp_pp': amp_1, 'offset': offset_1},
#                     'a_ch2'={'amp_pp': amp_2, 'offset': offset_2}
#                 )
#                 Outer keys (str)- the channel number (i.e. 'a_ch1' and 'a_ch2')
#                 Inner keys (str) - 'amp_pp' and 'offset'
#                 Items - the values for those channels [in Volts].

#                 If some channels/parameters are not mentioned, they are not changed.

#         :return: nested dict of the same structure as level_dict
#         """

#         for ch_name in level_dict.keys():
#             ch_num = int(ch_name.rsplit('_ch', 1)[1])

#             # set amplitude-pp
#             if 'amp_pp' in level_dict[ch_name].keys():
#                 self.write(
#                     'SOUR{}:VOLT:AMPL {}'.format(
#                         ch_num,
#                         level_dict[ch_name]['amp_pp']
#                     )
#                 )

#             # set offset
#             if 'offset' in level_dict[ch_name].keys():
#                 self.write(
#                     'SOUR{}:VOLT:OFFSET {}'.format(
#                         ch_num,
#                         level_dict[ch_name]['offset']
#                     )
#                 )

#         return self.get_analog_level()

#     def get_digital_level(self):
#         """ Retrieve the digital low and high level of all marker channels.

#         :return dict:
#                 {
#                     'd_ch1': {'low': 0.1, 'high': 1.2},
#                     'd_ch2': {'low': 0.0, 'high': 1.0},
#                     'd_ch3': {'low': 0.0, 'high': 1.0},
#                     'd_ch4': {'low': 0.0, 'high': 1.0}

#                 }
#         """

#         level_dict = dict()

#         for ch_name in self._get_all_dgtl_chs():
#             level_dict[ch_name] = dict()
#             d_ch_num = int(ch_name.rsplit('_ch', 1)[1])

#             # Convert into 'Analog channel + marker number'
#             a_ch_num = (d_ch_num + 1) // 2
#             d_ch_num -= 2 * (a_ch_num - 1)

#             # Low
#             level_dict[ch_name]['low'] = float(
#                 self.query(
#                     'SOUR{}:MARK{}:VOLT:LOW?'.format(a_ch_num, d_ch_num)
#                 )
#             )
#             # High
#             level_dict[ch_name]['high'] = float(
#                 self.query(
#                     'SOUR{}:MARK{}:VOLT:HIGH?'.format(a_ch_num, d_ch_num)
#                 )
#             )

#         return level_dict

#     def set_digital_level(self, level_dict):
#         """ Set low/high value of marker channels.

#         :param level_dict: nested dict of the following structure:
#             {
#                     'd_ch1': {'low': 0.1, 'high': 1.2},
#                     'd_ch2': {'low': 0.0, 'high': 1.0},
#                     'd_ch3': {'low': 0.0, 'high': 1.0},
#                     'd_ch4': {'low': 0.0, 'high': 1.0}

#             }
#         If some channels/markers/values are not mentioned, corresponding values
#         are not changed.

#         :return dict: the actual levels.
#         """

#         # Determine the requested final state:
#         #   get current state
#         req_dict = self.get_digital_level()
#         #   update it with the new values from level_dict
#         for d_ch_name in level_dict.keys():
#             try:
#                 if 'low' in level_dict[d_ch_name]:
#                     req_dict[d_ch_name]['low'] = level_dict[d_ch_name]['low']

#                 if 'high' in level_dict[d_ch_name]:
#                     req_dict[d_ch_name]['high'] = level_dict[d_ch_name]['high']

#             except KeyError:
#                 msg_str = 'set_digital_level(): channel {} is not available. \n' \
#                           'Currently available digital channels: \n' \
#                           '     {}'.format(d_ch_name, self._get_all_dgtl_chs())

#                 self.log.exception(msg_str=msg_str)
#                 raise PGenError(msg_str)

#         # Set all values
#         for d_ch_name in req_dict.keys():
#             d_ch_num = int(d_ch_name.rsplit('_ch', 1)[1])

#             # Convert into 'Analog channel + marker number'
#             a_ch_num = (d_ch_num + 1) // 2
#             d_ch_num -= 2 * (a_ch_num - 1)

#             # Low
#             self.write(
#                 'SOUR{}:MARK{}:VOLT:LOW {}'.format(
#                     a_ch_num,
#                     d_ch_num,
#                     req_dict[d_ch_name]['low']
#                 )
#             )

#             # High
#             self.write(
#                 'SOUR{}:MARK{}:VOLT:HIGH {}'.format(
#                     a_ch_num,
#                     d_ch_num,
#                     req_dict[d_ch_name]['high']
#                 )
#             )

#         # Check if the operation was successful
#         #   - check for explicit error messages was already performed in
#         #     self.write()

#         #   - check if the actual set values coincide with requested:
#         #     if the requested values do not satisfy hardware restrictions,
#         #     device will try to adjust previously set value [low] when setting
#         #     the next one [high]. This may mask the error: no explicit exception
#         #     will be produced, but the actual values will be different from expected.
#         actual_dict = self.get_digital_level()
#         if req_dict != actual_dict:
#             msg_str = 'set_digital_level(): the actual set value is different from expected: \n' \
#                       'requested = {} \n' \
#                       '   actual = {} \n' \
#                       'Most probably the requested values do not satisfy hardware restrictions ' \
#                       'on min/max amplitude [high-low] or overall voltage window.' \
#                       ''.format(req_dict, actual_dict)

#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return self.get_digital_level()

#     def get_interleave(self):
#         """ Check whether Interleave is ON or OFF in AWG.

#         :return bool: True: ON, False: OFF

#         Will always return False for pulse generator hardware without interleave.
#         """

#         if self._has_interleave():
#             return bool(int(
#                 self.query('AWGC:INT:STAT?')
#             ))
#         else:
#             return False

#     def set_interleave(self, state):
#         """ Turns the interleave of an AWG on or off.

#         :param bool state: The state the interleave should be set to
#                            (True: ON, False: OFF)

#         :return bool: actual interleave status (True: ON, False: OFF)
#         """

#         if self._has_interleave():
#             self.write(
#                 'AWGC:INT:STAT {}'.format(int(state))
#             )

#         # Enable all markers for all active analog channels
#         # (set DAC resolution to 8)
#         # FIXME: implement more generic (devices with 14-bit DAC)

#         for a_ch_name in self._get_all_anlg_chs():
#             a_ch_num = int(a_ch_name.rsplit('_ch', 1)[1])
#             self.write(
#                 'SOUR{}:DAC:RES {}'.format(
#                     a_ch_num,
#                     8
#                 )
#             )

#         return self.get_interleave()

#     def set_lowpass_filter(self, ch_num, cutoff_freq):
#         """ Set a lowpass filter to the analog channels of the AWG.

#         :param int ch_num: To which channel to apply, either 1 or 2.
#         :param cutoff_freq: Cutoff Frequency of the lowpass filter in Hz.

#         :return: (int) success code 0. Exception is produced in the case of error.
#         """

#         # Low-pass filter is not available on instruments with options 02 and 06
#         if '02' in self.option_list or '06' in self.option_list:
#             msg_str = 'set_lowpass_filter(): low-pass filter is not available for options [02] and [06].'
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         self.write(
#             'OUTPUT{}:FILTER:LPASS:FREQUENCY {}'
#             ''.format(ch_num, cutoff_freq)
#         )

#         return 0

#     #  Technical methods

#     def _get_all_chs(self):
#         """Helper method to return a sorted list of all technically available
#         channel names (e.g. ['a_ch1', 'a_ch2', 'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4'])

#         :return list: Sorted list of channel names
#         """

#         # Determine number of available channels based on model
#         if self.model == 'AWG7122C':
#             available_chs = ['a_ch1', 'd_ch1', 'd_ch2']

#             if not self.get_interleave():
#                 available_chs.extend(['a_ch2', 'd_ch3', 'd_ch4'])

#         else:
#             msg_str = 'Failed to determine number of available channels: \n' \
#                       'number of channels is not specified for "{}" model. ' \
#                       'Add this model to _get_all_chs()' \
#                       ''.format(self.model)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return sorted(available_chs)

#     def _get_all_anlg_chs(self):
#         """
#         Helper method to return a sorted list of all technically available analog channel
#         descriptors (e.g. ['a_ch1', 'a_ch2'])

#         :return list: Sorted list of analog channels
#         """

#         return sorted(
#             ch for ch in self._get_all_chs() if ch.startswith('a')
#         )

#     def _get_all_dgtl_chs(self):
#         """
#         Helper method to return a sorted list of all technically available digital channel
#         descriptors (e.g. ['d_ch1', 'd_ch2'])

#         :return list: Sorted list of digital channels
#         """

#         return sorted(
#             ch for ch in self._get_all_chs() if ch.startswith('d')
#         )

#     @staticmethod
#     def _is_digital(ch_name):
#         if 'd' in ch_name:
#             return True
#         else:
#             return False

#     def _zeroing_enabled(self):
#         """
#         Checks if the zeroing option is enabled. Only available on devices with option '06'.

#         @return bool: True: enabled, False: disabled
#         """
#         if self._has_interleave():
#             return bool(int(self.query('AWGC:INT:ZER?')))
#         return False

#     def _has_interleave(self):
#         """ Check if the device has the interleave option installed

#             :return bool: device has interleave option
#         """

#         return '06' in self.option_list

#     # -------------------------------------------------------------------------
#     # Waveform
#     # -------------------------------------------------------------------------

#     def fill_unused_chs(self, pb_obj):
#         """Fill all unused channels with default values:
#             DFalse() for marker channels
#             DConst(val=0.0) for analog channels
#         (channel mapping from user-friendly names [like 'AOM' and 'Ctr']
#         to device-native names [like 'a_ch1', 'd_ch2'] has to be performed
#         before calling this function)

#         :param pb_obj: PulseBlock object
#         :return: new PulseBlock object with all unused channels
#                  filled with default values.
#         """

#         pb_obj = copy.deepcopy(pb_obj)

#         pb_ch_set = set(pb_obj.p_dict.keys()) | set(pb_obj.dflt_dict.keys())
#         avail_ch_set = set(self._get_all_chs())

#         # Sanity check: all requested channels are available
#         if not pb_ch_set.issubset(avail_ch_set):
#             msg_str = 'write_wfm(): the following channels of the PulseBlock are not available: \n' \
#                       '{} \n' \
#                       ''.format(sorted(list(pb_ch_set - avail_ch_set)))

#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         # All available channels have to have a waveform assigned.
#         # If some channels are not used in the pb_obj,
#         # fill them with default value pulses
#         unused_ch_set = avail_ch_set - pb_ch_set
#         for unused_ch_name in unused_ch_set:
#             if self._is_digital(unused_ch_name):
#                 pb_obj.dflt_dict[unused_ch_name] = po.DFalse()
#             else:
#                 pb_obj.dflt_dict[unused_ch_name] = po.DConst(val=0.0)

#         return pb_obj

#     def write_wfm(self, pb_obj, len_adj=True, strict_hrdw_seq=False):
#         """Write plain waveform to AWG memory

#         :param pb_obj: PulseBlock object
#         :param len_adj: (bool) [argument of pb_sample()]
#             Add trailing default points to the end of the waveform to meet
#             length constraints.
#         :param strict_hrdw_seq: (bool) [argument of pb_sample()]
#             if True, strict waveform length constraints will be checked
#             (necessary for Hardware Sequence to operate in Sequence run mode)

#         :return int: 0 - success code.
#                      PGenError, ValueError, and other exceptions are produced
#                      in the cases of errors.
#         """

#         # Get waveform length constraints
#         wfm_len_constr = self.get_wfm_len_constr(strict_hrdw_seq=strict_hrdw_seq)

#         # Sample pulse block
#         samp_dict, n_samp_pts, add_samp_pts = pb_sample(
#             pb_obj=pb_obj,
#             samp_rate=self.get_samp_rate(),
#             len_min=wfm_len_constr['min'],
#             len_max=wfm_len_constr['max'],
#             len_step=wfm_len_constr['step'],
#             len_adj=len_adj,
#             debug=False
#         )

#         # Write waveform to the AWG memory
#         self._write_wfm(
#             samp_dict=samp_dict,
#             wfm_name=pb_obj.name
#         )

#         return 0

#     def write_wfm_zip(self, pb_obj, len_adj=True):
#         """ Write waveform as a sub-sequence with wait periods
#         collapsed into repetitions of the same short wait waveform.

#         :param pb_obj: PulseBlock object to write
#         :param len_adj: (bool) if True, the waveform will be padded with
#             leading default-value points to meet waveform length constraints.
#             If False and length does not meet constraints (min, max, step),
#             ValueError will be produced. Note that if length exceeds max,
#             ValueError is always produced.

#         :return: 0 - success
#             PGenError, ValueError, or another exception is produced in the case
#             of error.
#         """

#         len_constr_dict = self.get_wfm_len_constr(strict_hrdw_seq=True)
#         len_min = len_constr_dict['min']
#         len_max = len_constr_dict['max']
#         len_step = len_constr_dict['step']

#         samp_rate = self.get_samp_rate()

#         # Zip (collapse) pulse block ------------------------------------------

#         dur_quant = len_min / samp_rate
#         zip_dict = pb_zip(
#             pb_obj=pb_obj,
#             dur_quant=dur_quant
#         )
#         self.log.debug(msg_str='write_wfm_zip(): completed pb_zip() call')

#         # Sample and write all individual waveform snippets -------------------

#         snip_list = zip_dict['snip_list']
#         for snip_idx in range(len(snip_list)):
#             # Only the last snippet can have length different from len_min
#             # - external argument len_adj should be passed when sampling it
#             # - no sanity check for len % len_min == 0 is required for it
#             is_last = (
#                 snip_idx == len(snip_list) - 1
#             )

#             samp_dict, n_samp_pts, _ = pb_sample(
#                 pb_obj=snip_list[snip_idx],
#                 samp_rate=samp_rate,
#                 len_min=len_min,
#                 len_max=len_max,
#                 len_step=len_step,
#                 len_adj=len_adj if is_last else False
#             )
#             # Sanity check:
#             #   all snippets (except the last one) are expected to be of len_min
#             #   (corresponding to dur_quant).
#             #   Only the last element can be length-adjusted
#             #   (where adjustment is equivalent to total wfm len adjustment)
#             if not is_last and n_samp_pts % len_min != 0:
#                 msg_str = 'write_wfm_zip(): sampling of pb_snip={} ' \
#                           'resulted in unexpected sample array length {}. \n' \
#                           'The expectation was integer multiple of the hardware min {}. \n' \
#                           'Having precise length is necessary for operation ' \
#                           'of hardware sequencer.' \
#                           ''.format(
#                               snip_list[snip_idx].name,
#                               n_samp_pts,
#                               len_min
#                           )
#                 self.log.error(msg_str=msg_str)
#                 raise PGenError(msg_str)

#             self._write_wfm(
#                 samp_dict=samp_dict,
#                 wfm_name=snip_list[snip_idx].name
#             )

#         self.log.debug(
#             msg_str='write_wfm_zip(): completed sampling and loading all '
#                     'individual waveform snippets'
#         )

#         # Construct sub-sequence ----------------------------------------------

#         if pb_obj.name in self.subseq_get_names():
#             self.subseq_del(name=pb_obj.name)

#         seq_len = len(zip_dict['seq_list'])
#         self.subseq_new(
#             name=pb_obj.name,
#             length=seq_len
#         )

#         self.log.debug(
#             msg_str='write_wfm_zip(): created new sub-sequence. \n'
#                     'Start filling-in sequence table'
#         )

#         # Fill-in sequence steps
#         for elem_idx in range(seq_len):
#             elem_wfm_name, elem_rep = zip_dict['seq_list'][elem_idx]

#             # Set waveforms
#             for a_ch_name in self._get_all_anlg_chs():
#                 self.subseq_set_wfm(
#                     subseq_name=pb_obj.name,
#                     elem_num=elem_idx + 1,
#                     a_ch_name=a_ch_name,
#                     wfm_name=elem_wfm_name + a_ch_name[1:]
#                 )

#             # Set repetition
#             self.subseq_set_rep(
#                 subseq_name=pb_obj.name,
#                 elem_num=elem_idx + 1,
#                 rep_num=elem_rep
#             )

#         return 0

#     def load_wfm(self, load_dict):
#         """Load wfm_name from 'User defined' list to specified channel of AWG.

#         :param load_dict: a dictionary with keys being one of the channel number
#                           and values being the name of the already written wfm_name
#                           to load into the channel.
#                           Examples:   {1: 'rabi_ch1', 2: 'rabi_ch2'}

#         :return dict: Dictionary containing the actually loaded waveforms per channel.
#         """

#         # Load waveforms into channels
#         for ch_num, wfm_name in load_dict.items():

#             # load into channel
#             self.write('SOUR{0:d}:WAV "{1}"'.format(ch_num, wfm_name))

#         return self.get_loaded_assets()

#     def get_wfm_names(self):
#         """ Retrieve the names on 'User defined' list.

#         :return list: 'User defined' list.
#         """

#         wfm_list_len = int(self.query('WLIS:SIZE?'))
#         wfm_list = list()
#         for index in range(wfm_list_len):
#             wfm_list.append(self.query('WLIS:NAME? {0:d}'.format(index)))
#         return sorted(wfm_list)

#     def del_wfm(self, wfm_name):
#         """ Delete waveform_name from 'User Defined' list.

#         :param str wfm_name: The name/list of names of the waveform to be deleted
#                            Optionally 'all' can be passed to delete all waveforms.

#         :return int: 0 - success code.
#                      PGenError is produced in the case of error.
#         """

#         # Delete all
#         if wfm_name == 'all':
#             self.write('WLIS:WAV:DEL ALL')
#             return 0

#         # Delete specified
#         else:
#             if isinstance(wfm_name, str):
#                 wfm_name = [wfm_name]
#             wfm_list = wfm_name

#             for wfm in wfm_list:
#                 self.write('WLIS:WAV:DEL "{0}"'.format(wfm))

#             return 0

#     # Waveform technical methods

#     def _calc_byte_ar(self, amp_pp, offset, anlg_ar, mrk1_ar, mrk2_ar):

#         v_min = offset - amp_pp/2
#         v_max = offset + amp_pp/2
#         v_step = amp_pp / (2**8 - 1)

#         # Sanity check: all values of anlg_ar are within DAC range
#         ar_min = np.amin(anlg_ar)
#         ar_max = np.amax(anlg_ar)

#         if not v_min <= ar_min:
#             msg_str = '_calc_byte_ar(): min requested value {} is below DAC min {}' \
#                       ''.format(ar_min, v_min)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         if not ar_max <= v_max:
#             msg_str = '_calc_byte_ar(): max requested value {} is above DAC max {}' \
#                       ''.format(ar_max, v_max)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         # Calculate DAC bits (closest integer number of v_step)
#         a_int_ar = (anlg_ar - v_min) // v_step

#         # Bit offset (see AWG docs)
#         a_offs = 2 ** 2
#         m1_offs = 2 ** 13
#         m2_offs = 2 ** 14

#         byte_ar = np.asarray(
#             a=mrk2_ar*m2_offs + mrk1_ar*m1_offs + a_int_ar*a_offs,
#             dtype=np.uint16
#         )

#         return byte_ar

#     def _write_wfm(self, samp_dict, wfm_name):

#         # Get analog levels (will be used to calculate DAC bits)
#         anlg_level_dict = self.get_analog_level()

#         # Write waveforms. One for each analog channel.
#         for a_ch_name in self._get_all_anlg_chs():

#             # Calculate bytes array -------------------------------------------

#             start_t = time.time()

#             # Get the analog channel number
#             a_ch_num = int(a_ch_name.rsplit('ch', 1)[1])
#             # Get the corresponding digital channel names
#             mrk1_name = 'd_ch{0:d}'.format(a_ch_num * 2 - 1)
#             mrk2_name = 'd_ch{0:d}'.format(a_ch_num * 2)

#             byte_ar = self._calc_byte_ar(
#                 amp_pp=anlg_level_dict[a_ch_name]['amp_pp'],
#                 offset=anlg_level_dict[a_ch_name]['offset'],
#                 anlg_ar=samp_dict[a_ch_name],
#                 mrk1_ar=samp_dict[mrk1_name],
#                 mrk2_ar=samp_dict[mrk2_name]
#             )

#             self.log.debug(
#                 'Calculated byte data: {:.3f} s'.format(time.time() - start_t)
#             )

#             # Write bytes array to local HDD file -----------------------------

#             start = time.time()

#             # Create waveform name string
#             file_name = '{0}_ch{1:d}'.format(wfm_name, a_ch_num)
#             # Write WFM to a file on local HDD
#             self._write_wfm_file(
#                 filename=file_name,
#                 byte_ar=byte_ar
#             )

#             self.log.debug(
#                 'Wrote WFM file to local HDD: {:.3f} s'.format(time.time() - start)
#             )

#             # Send file to AWG over FTP ---------------------------------------

#             start = time.time()
#             self._send_file(filename=file_name)
#             self.log.debug(
#                 'Sent WFM file to AWG HDD: {:.3f} s'.format(time.time() - start)
#             )

#             # Load waveform to the AWG fast memory ----------------------------
#             # (waveform will appear on "User Defined" list)

#             start = time.time()

#             # Set AWG current working dir to 'C:\\inetpub\\ftproot\\remote_wfm_dir'
#             self.write(
#                 'MMEM:CDIR "{0}"'
#                 ''.format(
#                     os.path.join('C:\\inetpub\\ftproot', self._remote_wfm_dir)
#                 )
#             )
#             self.write(
#                 'MMEM:IMP "{0}","{1}",PAT'
#                 ''.format(
#                     file_name,
#                     file_name + '.pat'
#                 )
#             )  # This operation can take about 10 s to complete for 64 MSa waveform

#             self.log.debug(
#                 'Loaded WFM file into "User Defined" list: {:.3f} s'
#                 ''.format(time.time() - start)
#             )

#         return 0

#     def _write_wfm_file(self, filename, byte_ar):
#         """ Write byte_ar to binary file filename

#         :param byte_ar: numpy array of np.uint16 data type
#         :param filename: string, represents the name of the sampled waveform
#         :return int: status code: 0 - success
#                      PGenError exception is produced in the case of error
#         """

#         total_samp_num = len(byte_ar)

#         # Create the WFM file.
#         if not filename.endswith('.pat'):
#             filename += '.pat'
#         wfm_path = os.path.join(self._local_wfm_dir, filename)

#         #   - write header
#         with open(wfm_path, 'wb') as wfm_file:
#             num_bytes = str(total_samp_num * 2)
#             num_digits = str(len(num_bytes))
#             header = 'MAGIC 2000\r\n#{0}{1}'.format(num_digits, num_bytes)
#             wfm_file.write(header.encode())

#         # Write byte_ar to file
#         with open(wfm_path, 'ab') as wfm_file:
#             wfm_file.write(byte_ar)

#         # Append the footer: the sample rate, which was used for that file
#         footer = 'CLOCK {0:16.10E}\r\n'.format(self.get_samp_rate())
#         with open(wfm_path, 'ab') as wfm_file:
#             wfm_file.write(footer.encode())

#         return 0

#     def _send_file(self, filename):
#         """ Send binary file filename over FTP

#         :param filename: file name
#         :return: status code: 0 - Ok
#                  Exception is produced in the case of error
#         """

#         if not filename.endswith('.pat'):
#             filename += '.pat'
#         filepath = os.path.join(self._local_wfm_dir, filename)

#         # Sanity check: file is present
#         if not os.path.isfile(filepath):
#             msg_str = '_send_file: No file "{0}" found in "{1}". Unable to send!'\
#                       ''.format(filename, self._local_wfm_dir)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         # Delete old file on AWG by the same filename
#         if filename in self._remote_dir_list():
#             self._del_remote_file(filename)

#         # Transfer file
#         with FTP(self._ftp_ip_str) as ftp:
#             ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
#             ftp.cwd(self._remote_wfm_dir)
#             with open(filepath, 'rb') as file:  # In this case "file" refers to the file on user's PC
#                 ftp.storbinary('STOR ' + filename, file)

#         return 0

#     def _del_remote_file(self, filename):
#         """ Delete file from AWG HDD

#         File must be in 'C:\\inetpub\\ftproot\\remote_wfm_dir' directory

#         :param str filename: The full filename to delete from FTP cwd
#         :return int: status code: 0 -Ok
#         """

#         with FTP(self._ftp_ip_str) as ftp:
#             ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
#             ftp.cwd(self._remote_wfm_dir)
#             ftp.delete(filename)

#         return 0

#     def _remote_dir_list(self):
#         """ Get list of all files in 'C:\\inetpub\\ftproot\\remote_wfm_dir' directory.

#         :return list: list of file name strings
#         """

#         filename_list = list()
#         with FTP(self._ftp_ip_str) as ftp:
#             ftp.login(user=self._ftp_username, passwd=self._ftp_pswrd)
#             ftp.cwd(self._remote_wfm_dir)
#             # get only the files from the dir and skip possible directories
#             log = list()
#             ftp.retrlines('LIST', callback=log.append)
#             for line in log:
#                 if '<DIR>' not in line:
#                     # that is how a potential line is looking like:
#                     #   '05-10-16  05:22PM                  292 SSR aom adjusted.seq'
#                     # The first part consists of the date information. Remove this information and
#                     # separate the first number, which indicates the size of the file. This is
#                     # necessary if the filename contains whitespaces.
#                     size_filename = line[18:].lstrip()
#                     # split after the first appearing whitespace and take the rest as filename.
#                     # Remove for safety all trailing and leading whitespaces:
#                     filename = size_filename.split(' ', 1)[1].strip()
#                     filename_list.append(filename)

#         return filename_list

#     def get_wfm_len_constr(self, strict_hrdw_seq=False):
#         """Get waveform length constraints

#         :param strict_hrdw_seq: whether strict hardware sequencing
#         is required (imposes strong length constraints, required for
#         using Sequnce mode to collapse large waveforms)

#         :return: (dict) constraints dictionary, depending on
#             strrict_hrdw_seq parapeter and interleave state:
#             {
#                 'min': minimal length,
#                 'max': maximal length,
#                 'step': granularity
#             }
#         """

#         # FIXME: this is not general.

#         # Constraints depend on whether interleave is enabled or not
#         interleave = self.get_interleave()

#         # Hardware sequencing is strictly required
#         # (for using Sequence run mode to collapse large waveforms)
#         if strict_hrdw_seq:
#             if interleave:
#                 return {
#                     'min': 1920,
#                     'max': int(19.5e6),
#                     'step': 8
#                 }
#             else:
#                 return {
#                     'min': 960,
#                     'max': int(19.5e6),
#                     'step': 4
#                 }

#         # No requirement to use Hardware Sequencer only
#         # (just to output a plain waveform without memory-saving sequencing)
#         # Constraints are much softer in this case
#         else:
#             if interleave:
#                 return {
#                     'min': 1,
#                     'max': int(19.5e6),
#                     'step': 1
#                 }
#             else:
#                 return {
#                     'min': 1,
#                     'max': int(19.5e6),
#                     'step': 1
#                 }

#     # -------------------------------------------------------------------------
#     # Sequence and sub-sequence
#     # -------------------------------------------------------------------------

#     # Basic

#     def seq_get_len(self):
#         return int(
#             self.query('SEQUENCE:LENGTH?')
#         )

#     def seq_set_len(self, seq_len):
#         self.write(
#             'SEQUENCE:LENGTH {}'.format(seq_len)
#         )

#         return self.seq_get_len()

#     def seq_get_wfm(self, elem_num, a_ch_name):
#         a_ch_num = int(
#             a_ch_name.rsplit('_ch', 1)[1]
#         )

#         return self.query(
#             'SEQUENCE:ELEMENT{}:WAVEFORM{}?'.format(
#                 elem_num,
#                 a_ch_num
#             )
#         )

#     def seq_set_wfm(self, elem_num, a_ch_name, wfm_name):
#         a_ch_num = int(
#             a_ch_name.rsplit('_ch', 1)[1]
#         )

#         self.write(
#             'SEQUENCE:ELEMENT{}:WAVEFORM{} "{}"'.format(
#                 elem_num,
#                 a_ch_num,
#                 wfm_name
#             )
#         )

#         return self.seq_get_wfm(
#             elem_num=elem_num,
#             a_ch_name=a_ch_name
#         )

#     def seq_set_subseq(self, elem_num, subseq_name):
#         self.write(
#             'SEQUENCE:ELEMENT{}:SUBSEQUENCE "{}"'.format(
#                 elem_num,
#                 subseq_name
#             )
#         )

#         return self.query(
#             'SEQUENCE:ELEMENT{}:SUBSEQUENCE?'.format(elem_num)
#         )

#     def seq_get_twait(self, elem_num):
#         return bool(int(
#             self.query(
#                 'SEQUENCE:ELEMENT{}:TWAIT?'.format(elem_num)
#             )
#         ))

#     def seq_set_twait(self, elem_num, trig_enable):
#         self.write(
#             'SEQUENCE:ELEMENT{}:TWAIT {}'.format(
#                 elem_num,
#                 int(trig_enable)
#             )
#         )

#         return self.seq_get_twait(elem_num=elem_num)

#     def seq_get_rep(self, elem_num):
#         """ Get repetition number of elem_num

#         :param elem_num: (int) sequence element number
#                          [1 corresponds to the first element]
#         :return: (int) 0 - infinite
#                        positive integer - number of repetitions
#         """

#         is_inf = bool(int(
#             self.query(
#                 'SEQUENCE:ELEMENT{}:LOOP:INFINITE?'.format(elem_num)
#             )
#         ))

#         if is_inf:
#             return 0
#         else:
#             return int(
#                 self.query(
#                     'SEQUENCE:ELEMENT{}:LOOP:COUNT?'.format(elem_num)
#                 )
#             )

#     def seq_set_rep(self, elem_num, rep_num):
#         """ Set repetition number of elem_num

#         :param elem_num: (int) sequence element number
#                          [1 corresponds to the first element]
#         :param rep_num: (int) 0 - infinite
#                         positive integer - number of repetitions
#         :return: (int) actual number of repetitions
#         """

#         if rep_num == 0:
#             self.write(
#                 'SEQUENCE:ELEMENT{}:LOOP:INFINITE 1'.format(elem_num)
#             )
#         elif rep_num > 0:
#             self.write(
#                 'SEQUENCE:ELEMENT{}:LOOP:INFINITE 0'.format(elem_num)
#             )
#             self.write(
#                 'SEQUENCE:ELEMENT{}:LOOP:COUNT {}'.format(
#                     elem_num,
#                     rep_num
#                 )
#             )
#         else:
#             msg_str = 'seq_set_rep(): invalid argument rep_num = {}. \n' \
#                       'Valid values: 0 - for inf, positive integer - for finite' \
#                       ''.format(rep_num)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return self.seq_get_rep(elem_num=elem_num)

#     def seq_get_goto(self, elem_num):
#         """Get go-to target for elem_num sequence element

#         :param elem_num: (int) number of seq element [first seq elem is 1]
#         :return: (int) actual target:
#                 0 - 'go to the next'
#                 positive integer - non-trivial target
#         """

#         is_enabled = bool(int(
#             self.query(
#                 'SEQUENCE:ELEMENT{}:GOTO:STATE?'.format(elem_num)
#             )
#         ))

#         if not is_enabled:
#             return 0
#         else:
#             return int(
#                 self.query(
#                     'SEQUENCE:ELEMENT{}:GOTO:INDEX?'.format(elem_num)
#                 )
#             )

#     def seq_set_goto(self, elem_num, target):
#         """Set go-to target for elem_num sequence element

#         :param elem_num: (int) number of seq element [first seq elem is 1]
#         :param target: (int) 0 - 'go to the next'
#                              positive integer - non-trivial target
#         :return: (int) actual target
#         """

#         if target == 0:
#             # Set trivial go-to (go to the next)
#             self.write(
#                 'SEQUENCE:ELEMENT{}:GOTO:STATE 0'.format(elem_num)
#             )

#         elif target > 0:
#             # Enable non-trivial go-to
#             self.write(
#                 'SEQUENCE:ELEMENT{}:GOTO:STATE 1'.format(elem_num)
#             )
#             # Set go-to target
#             self.write(
#                 'SEQUENCE:ELEMENT{}:GOTO:INDEX {}'.format(
#                     elem_num,
#                     target
#                 )
#             )

#         else:
#             msg_str = 'seq_set_goto(): invalid argument target {}. \n' \
#                       'Valid values are: \n' \
#                       '     0 - "go to the next" \n' \
#                       '     positive integer - target' \
#                       ''.format(target)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return self.seq_get_goto(elem_num=elem_num)

#     # Event / dynamic jump

#     def get_jmp_mode(self):
#         mode_str = self.query('AWGControl:EVENt:JMODe?')
#         if mode_str == 'EJUM':
#             return 'EJUMP'
#         elif mode_str == 'DJUM':
#             return 'DJUMP'
#         else:
#             msg_str = 'get_jmp_mode(): unknown jump mode string {} was returned' \
#                       ''.format(mode_str)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#     def set_jmp_mode(self, mode_str):
#         """ Set sequence jump mode: Event Jump or Dynamic Jump.

#         :param mode_str: 'EJUMP' - Event Jump
#                          'DJUMP' - Dynamic Jump
#         :return: actual jump mode string
#         """

#         self.write(
#             'AWGCONTROL:EVENT:JMODE {}'.format(mode_str)
#         )
#         return self.get_jmp_mode()

#     def get_jmp_timing(self):
#         return self.query('EVENT:JTIMING?')

#     def set_jmp_timing(self, sync=True):
#         if sync:
#             self.write('EVENT:JTIMING SYNCHRONOUS')
#         else:
#             self.write('EVENT:JTIMING ASYNCHRONOUS')

#         return self.get_jmp_timing()

#     def get_ejmp_trgt(self, elem_num):
#         """ Get Event Jump target (use get/set_djmp_trgt for Dynamic Jump mode)

#         :param elem_num: (int) sequence element number
#         (1 corresponds to the first sequence element)
#         :return: (int) target sequence element number
#                        -1 - ignore event signal for this element
#                         0 - jump to the next
#          positive integer - jump to the specified element
#         """

#         jmp_type_str = self.query(
#             'SEQUENCE:ELEMENT{}:JTARGET:TYPE?'.format(elem_num)
#         )

#         # Ignore event signal for this element
#         if jmp_type_str == 'OFF':
#             return -1

#         # Jump to the next
#         elif jmp_type_str == 'NEXT':
#             return 0

#         # Jump to the specified index
#         elif jmp_type_str == 'IND':
#             target_str = self.query(
#                 'SEQUENCE:ELEMENT{}:JTARGET:INDEX?'.format(elem_num)
#             )
#             return int(target_str)

#         # Unknown type
#         else:
#             msg_str = 'get_ejmp_trgt(): query for elem_num={} returned unknown jump type string {}' \
#                       ''.format(elem_num, jmp_type_str)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#     def set_ejmp_trgt(self, elem_num, target):
#         """ Set Event Jump target (use get/set_djmp_trgt for Dynamic Jump mode)

#         :param elem_num: (int) sequence element number
#         (1 corresponds to the first sequence element)

#         :param target: (int) target sequence element number
#                        -1 - ignore event signal for this element
#                         0 - jump to the next
#          positive integer - jump to the specified element

#         :return: (int) actual jump target.
#         """

#         # No Event jump action for this sequence element
#         if target < 0:
#             self.write(
#                 'SEQUENCE:ELEMENT{}:JTARGET:TYPE OFF'.format(elem_num)
#             )

#         # Jump to the next
#         elif target == 0:
#             self.write(
#                 'SEQUENCE:ELEMENT{}:JTARGET:TYPE NEXT'.format(elem_num)
#             )

#         # Jump to non-trivial index
#         else:
#             self.write(
#                 'SEQUENCE:ELEMENT{}:JTARGET:TYPE INDEX'.format(elem_num)
#             )
#             self.write(
#                 'SEQUENCE:ELEMENT{}:JTARGET:INDEX {}'.format(elem_num, target)
#             )

#         return self.get_ejmp_trgt(elem_num=elem_num)

#     def get_djmp_trgt(self, bit_patrn_int):
#         """ Get Dynamic Jump target for the specified bit pattern

#         :param bit_patrn_int: integer representation of bit patter:
#                               '0000 0101' is specified as 5
#         :return: (int) target element for this bit pattern
#         """

#         return int(self.query(
#             'AWGCONTROL:EVENT:DJUMP:DEFINE? {}'.format(
#                 bit_patrn_int
#             )
#         ))

#     def set_djmp_trgt(self, bit_patrn_int, trgt_elem):
#         """ Set Dynamic Jump target for the specified bit pattern

#         :param bit_patrn_int: integer representation of bit patter:
#                               '0000 0101' is specified as 5
#         :param trgt_elem: sequence element number to jump onto
#                           (1 corresponds to the first sequence element).
#                           Passing 0 disables dynamic jump for this bit
#                           pattern

#         :return: (int) actual target element for this bit pattern
#         """

#         self.write(
#             'AWGCONTROL:EVENT:DJUMP:DEFINE {},{}'.format(
#                 bit_patrn_int,
#                 trgt_elem
#             )
#         )
#         return self.get_djmp_trgt(bit_patrn_int=bit_patrn_int)

#     # Sub-sequence

#     def subseq_new(self, name, length):
#         self.write(
#             'SLIST:SUBSEQUENCE:NEW "{}",{}'.format(name, length)
#         )

#         return 0

#     def subseq_del(self, name):
#         """ Delete sub-sequence from sub-sequence list

#         :param name: (str) sub-sequence name or 'all'
#         :return: (int) 0 - success
#                  PGenError is produced in the case of error
#         """

#         if name == 'all':
#             self.write(
#                 'SLIST:SUBSEQUENCE:DELETE ALL'
#             )
#         else:
#             self.write(
#                 'SLIST:SUBSEQUENCE:DELETE "{}"'.format(name)
#             )

#         return 0

#     def subseq_get_len(self, name):
#         len_str = self.query(
#             'SLIST:SUBSEQUENCE:LENGTH? "{}"'.format(name)
#         )
#         return int(len_str)

#     def subseq_set_len(self, name, length):
#         self.write(
#             'SLISt:SUBSequence:LENGth "{}",{}'.format(
#                 name,
#                 length
#             )
#         )

#         return self.subseq_get_len(name=name)

#     def subseq_get_wfm(self, subseq_name, elem_num, a_ch_name):
#         a_ch_num = int(
#             a_ch_name.rsplit('_ch', 1)[1]
#         )

#         return self.query(
#             'SLIST:SUBSEQUENCE:ELEMENT{}:WAVEFORM{}? "{}"'.format(
#                 elem_num,
#                 a_ch_num,
#                 subseq_name
#             )
#         )

#     def subseq_set_wfm(self, subseq_name, elem_num, a_ch_name, wfm_name):
#         a_ch_num = int(
#             a_ch_name.rsplit('_ch', 1)[1]
#         )

#         self.write(
#             'SLIST:SUBSEQUENCE:ELEMENT{}:WAVEFORM{} "{}","{}"'.format(
#                 elem_num,
#                 a_ch_num,
#                 subseq_name,
#                 wfm_name
#             )
#         )

#         return self.subseq_get_wfm(
#             subseq_name=subseq_name,
#             elem_num=elem_num,
#             a_ch_name=a_ch_name
#         )

#     def subseq_get_rep(self, subseq_name, elem_num):
#         rep_num = int(self.query(
#             'SLIST:SUBSEQUENCE:ELEMENT{}:LOOP:COUNT? "{}"'.format(
#                 elem_num,
#                 subseq_name
#             )
#         ))

#         return rep_num

#     def subseq_set_rep(self, subseq_name, elem_num, rep_num):
#         self.write(
#             'SLIST:SUBSEQUENCE:ELEMENT{}:LOOP:COUNT "{}",{}'.format(
#                 elem_num,
#                 subseq_name,
#                 rep_num
#             )
#         )

#         return self.subseq_get_rep(
#             subseq_name=subseq_name,
#             elem_num=elem_num
#         )

#     def subseq_get_names(self):

#         ss_name_list = []

#         # Number of seb-sequences on the list
#         ss_list_len = int(
#             self.query('SLIST:SIZE?')
#         )

#         for idx in range(1, ss_list_len + 1):
#             ss_name_list.append(
#                 self.query('SLIST:NAME? {}'.format(idx))
#             )

#         return ss_name_list

#     # -------------------------------------------------------------------------
#     # Waveform and sequence technical
#     # -------------------------------------------------------------------------

#     def get_loaded_assets(self):
#         """
#         Retrieve the currently loaded asset names for each active channel of the device.
#         The returned dictionary will have the channel numbers as keys.
#         In case of loaded waveforms the dictionary values will be the waveform names.
#         In case of a loaded sequence the values will be the sequence name appended by a suffix
#         representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

#         @return (dict, str): Dictionary with keys being the channel number and values being the
#                              respective asset loaded into the channel,
#                              string describing the asset type ('waveform' or 'sequence')
#         """

#         # Get all active analog channels
#         a_ch_name_list = self._get_all_anlg_chs()
#         a_ch_num_list = sorted(
#             int(ch_name.split('_ch')[1]) for ch_name in a_ch_name_list
#         )

#         # Get assets per channel
#         loaded_assets = dict()

#         run_mode = self.query('AWGC:RMOD?')
#         if run_mode in ['CONT', 'TRIG', 'GAT']:
#             current_type = 'waveform'
#             for ch_num in a_ch_num_list:
#                 loaded_assets[ch_num] = self.query('SOUR{0}:WAV?'.format(ch_num))
#         elif run_mode == 'SEQ':
#             current_type = 'sequence'
#             for ch_num in a_ch_num_list:
#                 if len(self._loaded_seqs) > 0:
#                     loaded_assets[ch_num] = self._loaded_seqs[0]
#         else:
#             msg_str = 'get_loaded_assets(): received unknown run mode: {}'\
#                       ''.format(run_mode)
#             self.log.error(msg_str=msg_str)
#             raise PGenError(msg_str)

#         return loaded_assets, current_type

#     def clear_all(self):
#         """ Clears all loaded waveforms from the pulse generators RAM/workspace.
#         (from "User Defined" list)

#         @return int: error code (0:OK, -1:error)
#         """

#         self.write('WLIS:WAV:DEL ALL')
#         if '09' in self.option_list:
#             self.write('SLIS:SUBS:DEL ALL')

#         self.write('SEQUENCE:LENGTH 0')
#         self._written_seqs = []
#         self._loaded_seqs = []

#         return 0


# class Service(ServiceBase):
#     # TODO: implement
#     pass


# class Client(ClientBase):
#     # TODO: implement
#     pass
