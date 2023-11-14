# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware class
for the Zurich Instruments HDAWG.
"""

import zhinst.utils
import zhinst.ziPython
import re
import time
import textwrap
import copy
import re
import os
import json
import numpy as np

from pylabnet.utils.logging.logger import LogHandler

from pylabnet.utils.decorators.logging_redirector import log_standard_output
from pylabnet.utils.decorators.dummy_wrapper import dummy_wrap


# Storing the sampling rates and the corresponding target integers for the setInt command
SAMPLING_RATE_DICT = {
    '2.4 GHz': 0,
    '1.2 GHz': 1,
    '600 MHz': 2,
    '300 MHz': 3,
    '150 MHz': 4,
    '75 MHz': 5,
    '37.5 MHz': 6,
    '18.75 MHz': 7,
    '9.37 MHz': 8,
    '4.68 MHz': 9,
    '2.34 MHz': 10,
    '1.17 MHz': 11,
    '585.93 kHz': 12,
    '292.96 kHz': 13,
}


class Driver():

    def __init__(self, device_id, interface, logger, dummy=False, api_level=6, reset_dio=False, disable_everything=False, **kwargs):
        """ Instantiate AWG

        :logger: instance of LogClient class
        :device_id: Device id of connceted ZI HDAWG, for example 'dev8060'
        :api_level: API level of zhins API
        """

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Store dummy flag
        self.dummy = dummy

        # Setup HDAWG
        self._setup_hdawg(device_id, interface, logger, api_level, reset_dio, disable_everything)

    @dummy_wrap
    def reset_DIO_outputs(self):
        """Sets all DIO outputs to low"""
        self.seti('dios/0/output', 0)
        self.log.info("Set all DIO outputs to low.")

    @dummy_wrap
    def disable_everything(self):
        """ Create a base configuration.
        Disable all available outputs, awgs, demods, scopes, etc.
        """
        zhinst.utils.disable_everything(self.daq, self.device_id)
        self.log.info("Disabled everything.")

    @log_standard_output
    @dummy_wrap
    def log_stdout(self, function):
        """ Execute function and log print output to self.log

        This statement is needed for an inline call where any zhinst command is
        executed and the standard output should be logged
        :function: The function to be executed.
         """
        return function()

    def _convert_to_list(self, input_argument):
        """Checks if input is list and if not, converts it to list."""
        if type(input_argument) is not list:
            input_argument = [input_argument]
        return input_argument

    @dummy_wrap
    def _setup_hdawg(self, device_id, interface, logger, api_level, reset_dio, disable_everything):
        ''' Sets up HDAWG '''
        # try finding the server address
        discovery = zhinst.ziPython.ziDiscovery()
        device_properties = discovery.get(discovery.find(device_id))
        server_address = device_properties["serveraddress"]

        server_host = "localhost"
        server_port = 8004
        api_level = 6  # Maximum API level supported for all instruments.

        # Create an API session to the Data Server.
        self.daq = zhinst.core.ziDAQServer(server_address, server_port, api_level)
        # Establish a connection between Data Server and Device.
        self.daq.connectDevice(device_id, interface)

        self.device_id = device_id

        if disable_everything:
            # Create a base configuration
            self.disable_everything()
        if reset_dio:
            self.reset_DIO_outputs()
        # read out number of channels from property dictionary
        self.num_outputs = int(
            re.compile('HDAWG(4|8{1})').match(device_properties['devicetype']).group(1)
        )
        self.log.info(f"Sucessfully connected to HDAWG {device_id} at {server_address}.")

    @log_standard_output
    @dummy_wrap
    def seti(self, node, new_int):
        """
        Warapper for daq.setInt commands. For instance, instead of
        daq.setInt('/dev8040/sigouts/0/on', 1), write

        hdawg.seti('sigouts/0/on, 1)

        :node: Node which will be appended to '/device_id/'
        :new_int: New value for integer
        """

        self.daq.syncSetInt(f'/{self.device_id}/{node}', new_int)

    @log_standard_output
    @dummy_wrap
    def setd(self, node, new_double):
        """
        Warapper for daq.setDouble commands. For instance, instead of
        daq.setDouble('/dev8040/sigouts/0/range', 0.8), write

        hdawg.setd('sigouts/0/range')

        :node: Node which will be appended to '/device_id/'
        :new_double: New value for double.
        """

        self.daq.syncSetDouble(f'/{self.device_id}/{node}', new_double)

    @log_standard_output
    @dummy_wrap
    def getd(self, node):
        """
        Warapper for daq.setDouble commands. For instance, instead of
        daq.getDouble('/dev8040/sigouts/0/range'), write

        hdawg.getd('sigouts/0/range')

        :node: Node which will be appended to '/device_id/'
        """

        return self.daq.getDouble(f'/{self.device_id}/{node}')

    @log_standard_output
    @dummy_wrap
    def setv(self, node, vector):
        """
        Warapper for daq.setVector commands. For instance, instead of
        daq.setVector('/dev8060/awgs/0/waveform/waves/1', vector), write

        hdawg.setd('sigouts/awgs/0/waveform/waves/1', vector)

        :node: Node which will be appended to '/device_id/'
        :new_double: New value for double.
        """

        self.daq.setVector(f'/{self.device_id}/{node}', vector)

    @log_standard_output
    @dummy_wrap
    def geti(self, node):
        """
        Wrapper for daq.getInt commands. For instance, instead of
        daq.getInt('/dev8040/sigouts/0/busy'), write

        hdawg.geti('sigouts/0/busy')

        :node: Node which will be appended to '/device_id/'
        """

        return self.daq.getInt(f'/{self.device_id}/{node}')

    @log_standard_output
    @dummy_wrap
    def gets(self, path):
        """
        Wrapper for daq.getString commands.
        Get a string value from the specified node.
|       :path: Path string of the node.
        """
        return self.daq.getString(path)

    @dummy_wrap
    def set_channel_grouping(self, index):
        """ Specifies channel grouping.

        :index: Integer indicating channel grouping:
            0 : 4x2 with HDAWG8; 2x2 with HDAWG4.
            1 : 2x4 with HDAWG8; 1x4 with HDAWG4.
            2 : 1x8 with HDAWG8.
        """
        self.seti('system/awg/channelgrouping', index)
        time.sleep(2)

    # Functions related to wave outputs:

    @dummy_wrap
    def _toggle_output(self, output_indices, target_index):
        """
        Local function enabeling/disabeling wave output.
        """

        # If single integer is given, convert to list.
        output_indices = self._convert_to_list(output_indices)

        for output_index in output_indices:
            if output_index in range(self.num_outputs):
                self.seti(f'sigouts/{output_index}/on', target_index)
                if target_index == 1:
                    self.log.info(f"Enabled wave output {output_index}.")
                elif target_index == 0:
                    self.log.info(f"Disable wave output {output_index}.")
            else:
                self.log.error(
                    f"This device has only {self.num_outputs} channels, \
                        channel index {output_index} is invalid."
                )

    @dummy_wrap
    def enable_output(self, output_indices):
        """
        Enables wave output.

        Channel designation uses channel index (0 to 7),
        not channel number (1 to 8).

        :output_index: List or int containing
            integers indicating wave output 0 to 7
        """

        self._toggle_output(output_indices, 1)

    @dummy_wrap
    def disable_output(self, output_indices):
        """
        Disables wave output.

        :output_index: List or int containing
            integers indicating wave output 0 to 7
        """
        self._toggle_output(output_indices, 0)

    @dummy_wrap
    def set_output_range(self, output_index, output_range):
        """
        Set the output range.

        :output_index: List or int containing integers
            indicating wave output 0 to 7
        :output_range: Double indicating the range of wave output, in Volt.
            All waveforms (ranging from 0 to 1 in value) will be multiplied
            with this value. Possible ranges are:
            0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5 (V)
        """

        allowed_ranges = [0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5]

        if output_index in range(self.num_outputs):
            if output_range in allowed_ranges:

                # Send change range command.
                self.setd(f'sigouts/{output_index}/range', output_range)

                # Wait for HDAWG to be ready, try 100 times before timeout.
                max_tries = 100
                num_tries = 0

                while self.geti(f'sigouts/{output_index}/busy') and num_tries < max_tries:
                    time.sleep(0.2)
                    num_tries += 1

                if num_tries is max_tries:
                    self.log.error(
                        f"Range change timeout after {max_tries} tries."
                    )
                else:
                    self.log.info(
                        f"Changed range of wave output {output_index} to {output_range} V."
                    )
            else:
                self.log.error(
                    f"Range {output_range} is not valid, allowed values for range are {allowed_ranges}"
                )
        else:
            self.log.error(
                f"This device has only {self.num_outputs} channels, channel index {output_index} is invalid."
            )

    def set_direct_user_register(self, awg_num, reg_index, value):
        """ Sets a user register to a desired value

        :param awg_num: (int) index of awg module
        :param reg_index: (int) index of user register (from 0-15)
        :param value: (int) value to set user register to
        """

        self.setd(f'awgs/{awg_num}/userregs/{reg_index}', int(value))

    def get_direct_user_register(self, awg_num, reg_index):
        """ Gets a user register to a desired value

        :param awg_num: (int) index of awg module
        :param reg_index: (int) index of user register (from 0-15)
        """

        return int(self.getd(f'awgs/{awg_num}/userregs/{reg_index}'))


class AWGModule():
    """ Wrapper class for awgModule"""

    def __init__(self, hdawg_driver, index):
        """ Setup AWG Module

        :index: Which AWG sequencer to be used
            0 - 3 for 4x2 channel grouping
            0 - 1 for 2x4 channel grouping
            0     for 1x8 channel grouping

         :hdawg_driver: Instance of HDAWG_Driver
        """

        self.hd = hdawg_driver
        self.index = index

        # Check if chosen index is allowed for current channel grouping.
        channel_grouping = hdawg_driver.geti('system/awg/channelgrouping')

        if channel_grouping == 0:
            num_awgs = 4
        elif channel_grouping == 1:
            num_awgs = 2
        elif channel_grouping == 2:
            num_awgs = 1

        allowed_indices = range(num_awgs)

        self.channel_grouping = channel_grouping
        self.num_awgs = num_awgs
        self.channels_per_awg = 8 // num_awgs

        if index not in allowed_indices:
            self.hd.log.error(
                f"Current channel grouping only allows for the following \
                     AWG indices {list(allowed_indices)}"
            )
            return None

        # Create an instance of the AWG Module
        awgModule = hdawg_driver.daq.awgModule()
        awgModule.set('index', index)
        awgModule.set('device', hdawg_driver.device_id)
        awgModule.execute()

        # Disable re-run function
        self.hd.seti(f'awgs/{self.index}/single', 1)

        self.module = awgModule
        self.hd.log.info(f"AWG {self.index}: Module created.")

    def set_sampling_rate(self, sampling_rate):
        """ Set sampling rate of AWG output

        :sampling_rate: String of target sampling rate:
            '2.4 GHz',
            '1.2 GHz',
            '600 MHz',
            '300 MHz',
            '150 MHz',
            '75 MHz',
            '37.5 MHz',
            '18.75 MHz',
            '9.37 MHz',
            '4.68 MHz',
            '2.34 MHz',
            '1.17 MHz',
            '585.93 kHz',
            '292.96 kHz'
        """

        possible_sampling_rates = SAMPLING_RATE_DICT.keys()
        if sampling_rate not in possible_sampling_rates:
            self.hd.log.error(f"AWG {self.index}: Invalid sampling rate '{sampling_rate}', possible choices are {list(possible_sampling_rates)}")
            return

        sampling_rate_index = SAMPLING_RATE_DICT[sampling_rate]

        self.hd.seti(f'awgs/{self.index}/time', sampling_rate_index)
        self.hd.log.info(
            f"AWG {self.index}: Changed sampling rate to {sampling_rate}."
        )

    def start(self, dio_mode_change=True):
        """ Start AWG"""

        if dio_mode_change:
            # Set DIO mode to AWG sequencer
            self.hd.seti('dios/0/mode', 1)

        self.module.set('awg/enable', 1)
        self.hd.log.info(f"AWG {self.index}: Started.")

    def stop(self):
        """ Stop AWG"""
        self.module.set('awg/enable', 0)
        self.hd.log.info(f"AWG {self.index}: Stopped.")

    def setup_dio(self, DIO_bits):
        """Enable driving of DIO buses of relevant DIO bits."""

        # Set DIO mode to AWG sequencer
        self.hd.seti('dios/0/mode', 1)

        # Read in current configuration of DIO-bus.
        current_config = self.hd.geti('dios/0/drive')

        for DIO_bit in DIO_bits:
            if DIO_bit in range(8):
                toggle_bit = 1  # 1000
            elif DIO_bit in range(8, 16):
                toggle_bit = 2  # 0100
            elif DIO_bit in range(16, 24):
                toggle_bit = 4  # 0010
            elif DIO_bit in range(24, 32):
                toggle_bit = 8  # 0001
            else:
                self.hd.log.error(
                    f"DIO_bit {DIO_bit} invalid, must be in range 0-31."
                )

            # Set new configuration by using the bitwise OR.
            new_config = current_config | toggle_bit
            self.hd.seti('dios/0/drive', new_config)

            # Update current configuration
            current_config = new_config

    def setup_analog(self, setup_configs, assignment_dict):
        """ Set up the AWG operation parameters that are required for the
        analog waveform playback.

        :setup_configs: (dict) keys are channel names, values are a dict of
            parameters to be set up for that channel. E.g.
                {  "mod": mod,  "mod_freq": mod_freq, "mod_ph": mod_ph}
            representing modulation settings for the channel.
        :assignment_dict: (dict) keys are channel names, values are a list
            ["analog" / "dio", channel_number].
        """

        for ch, config_dict in setup_configs.items():
            ch_type, ch_num = assignment_dict[ch]

            # Convert from specified 1-indexed to 0-indexed in the AWG code
            ch_num -= 1

            if ch_type != "analog":
                self.hd.log.warn(f"Attempted to setup a digital channel {ch} with analog functions.")

            for config_type, config_val in config_dict.items():

                if config_type == "mod":

                    # 0 = mod off, 1 = sin11, 2 = sin22, 3 = sin12, 4 = sin21
                    # Assume we want sin12 (i.e. AWG1 x Sin1 + AWG2 x Sin2)
                    mod = 3 if config_val else 0
                    # AWG number is always labeled in 4x2 mode regardless of sequencer settings
                    self.hd.seti(f'awgs/{ch_num//2}/outputs/{ch_num%2}/modulation/mode', mod)

                    # Oscillation oscillator index - set oscillator n to channel n
                    # Not applicable for non-MF mod.
                    self.hd.seti(f'sines/{ch_num}/oscselect', ch_num)

                elif config_type == "mod_freq":
                    # Assume that outputs 1-2 use osc 0, 3-4 use osc 1, etc.
                    self.hd.setd(f'oscs/{ch_num//2}/freq', config_val)
                    self.hd.log.info(f"Setting oscillator {ch_num//2} frequency to {config_val}.")

                elif config_type == "mod_ph":
                    self.hd.setd(f'sines/{ch_num}/phaseshift', config_val)
                    self.hd.log.info(f"Setting sine {ch_num} phase to {config_val}.")

                elif config_type == "amp_iq":
                    #self.hd.setd(f'sines/{ch_num}/amplitudes/{ch_num%2}', config_val)
                    self.hd.setd(f'awgs/{ch_num//2}/outputs/{ch_num%2}/gains/{ch_num%2}', config_val)
                    self.hd.log.info(f"Setting sine {ch_num} amplitude {ch_num%2} to {config_val}.")

                elif config_type == "dc_iq":
                    self.hd.setd(f'sigouts/{ch_num}/offset', config_val)
                    self.hd.log.info(f"Setting output {ch_num} offset to {config_val}.")

                elif config_type == "lo_freq":
                    self.hd.log.info(f"LO frequency of {config_val} found, AWG ignoring...")

                else:
                    self.hd.log.warn(f"Unsupported analog channel config {config_type}.")

            # Enable output
            self.hd.enable_output(ch_num)

    def compile_upload_sequence(self, sequence):
        """ Compile and upload AWG sequence to AWG Module.

        :sequence: Instance of Sequence class.
        """

        # First check if all values have been replaced in sequence:
        if not sequence.is_ready():
            self.hd.log.error("Sequence is not ready: Not all placeholders have been replaced.")
            return

        self.module.set('compiler/sourcestring', sequence.sequence)
        # Note: when using an AWG program from a source file
        # (and only then), the compiler needs to
        # be started explicitly with awgModule.set('compiler/start', 1)
        while self.module.getInt('compiler/status') == -1:
            time.sleep(0.1)

        if self.module.getInt('compiler/status') == 1:
            # compilation failed, raise an exception
            self.hd.log.warn(self.module.getString('compiler/statusstring'))
            return

        if self.module.getInt('compiler/status') == 0:
            self.hd.log.info(
                "Compilation successful with no warnings, will upload the program to the instrument."
            )
        if self.module.getInt('compiler/status') == 2:
            self.hd.log.warn(
                "Compilation successful with warnings, will upload the program to the instrument."
            )
            self.hd.log.warn(
                f"Compiler warning: {self.module.getString('compiler/statusstring')}"
            )

        # Wait for the waveform upload to finish
        time.sleep(0.2)
        i = 0
        while (self.module.getDouble('progress') < 1.0) and (self.module.getInt('elf/status') != 1):
            self.hd.log.info("{} progress: {:.2f}".format(i, self.module.getDouble('progress')))
            time.sleep(0.2)
            i += 1
        self.hd.log.info(
            "{} progress: {:.2f}".format(i, self.module.getDouble('progress'))
        )
        if self.module.getInt('elf/status') == 0:
            self.hd.log.info("Upload to the instrument successful.")
        if self.module.getInt('elf/status') == 1:
            self.hd.log.warn("Upload to the instrument failed.")

    def dyn_waveform_upload(self, wave_index, wave1, wave2=None, marker=None, index=None):
        """ Dynamically upload a numpy array into HDAWG Memory

        :wave_index: (int) index of waveform that can be accessed inside command table
            Must be < 16000. All waves in the sequencer program are automatically
            assigned a wave index or can be assigned with assignWaveIndex().
            Let N be the total # of waveforms and M>0 be the # of CSV-defined
            waveforms. Then the automatically-assigned waveform indices are:
            - 0,...,M-1 for waveforms defined from CSV files alphabetically
                ordered by filename,
            - M,...,N-1 in the order that the waveforms are defined in the
                sequencer program.
        :wave1: (numpy Array) waveform for Ouput 1
        :wave2: (numpy Array, optional) waveform for Ouput 2, similar to commands
            of the form playWave(wave1, wave2)
        :marker: (numpy Array, optional) waveform for the market output
        :index: (int, optional) AWG node number (0-3) to upload waveform to.
        """

        if index is None:
            index = self.index

        # Convert to HDAWG native format
        waveform_native = zhinst.utils.convert_awg_waveform(wave1, wave2, marker)

        # Upload waveform data to the desired index
        self.hd.setv(f"awgs/{index}/waveform/waves/{wave_index}", waveform_native)

    def save_waveform_csv(self, waveform, csv_filename):
        """ Saves a numpy array in CSV format into the HDAWG folder

        :waveform: np.array containing waveform
        :csv_filename: str of the CSV file to be named (should end in .csv)
        """

        # Get the modules data directory
        data_dir = self.module.getString("directory")

        # All CSV files within the waves directory are automatically recognized
        # by the AWG module
        wave_dir = os.path.join(data_dir, "awg", "waves")

        # The data directory is created by the AWG module and should always exist.
        # If this exception is raised, something might be wrong with the file system.
        if not os.path.isdir(wave_dir):
            raise Exception(f"AWG module wave directory {wave_dir} does not exist or is not a directory")

        if not csv_filename.endswith(".csv"):
            self.hd.log.warn(f"CSV filename {csv_filename} did not end in .csv, appending it to filename.")
            csv_filename += ".csv"

        # Save waveform data to CSV
        csv_file = os.path.join(wave_dir, csv_filename)
        np.savetxt(csv_file, waveform)

    def set_user_register(self, reg_index, value):
        """ Sets a user register to a desired value

        :param reg_index: (int) index of user register (from 0-15)
        :param value: (int) value to set user register to
        """

        self.hd.setd(f'awgs/{self.index}/userregs/{reg_index}', int(value))

    def upload_cmd_table(self, cmd_table_str, index=None):
        """ Upload command table JSON string into a given AWG node.

        :cmd_table_str: (str) JSON file containing the command table.
        :index: (int, optional) AWG node number (0-3) to upload waveform to.
        """

        if index is None:
            index = self.index

        # Validate if string is a valid JSON
        try:
            json.loads(cmd_table_str)
        except ValueError:
            self.hd.log.error("Command table string is invalid JSON format.")
            return False

        self.hd.setv(f"awgs/{index}/commandtable/data", cmd_table_str)
        return True


class Sequence():
    """ Helper class containing .seqc sequences and helper functions

    """

    def replace_placeholders(self, placeholder_dict):
        """ Replace a placeholder by some value

        :placeholder: Placeholder string to be replaced.
        :value: Value to which the placeholder string need to be set.
        """

        for placeholder, value in placeholder_dict.items():
            placeholder_wrapped = f"{self.marker_string}{placeholder}{self.marker_string}"

            if placeholder not in self.unresolved_placeholders:
                self.hd.log.warn(f"Placeholder {placeholder} not found in sequence.")
            else:
                self.sequence = self.sequence.replace(f"{placeholder_wrapped}", str(value))
                self.unresolved_placeholders.discard(placeholder)

    def replace_waveforms(self, waveform_dict):
        """ Replace a placeholder by a waveform

        :placeholder: Placeholder string to be replaced.
        :waveform: Numpy array designating the waveform.
        """
        for waveform, value in waveform_dict.items():

            if waveform not in self.unresolved_placeholders:
                self.hd.log.error(f"Placeholder {waveform} not found in sequence.")

            waveform_wrapped = f"{self.marker_string}{waveform}{self.marker_string}"
            waveform_vector = 'vect(' + ','.join([str(x) for x in value]) + ')'
            self.sequence = self.sequence.replace(f"{waveform_wrapped}", str(waveform_vector))
            self.unresolved_placeholders.discard(waveform)

    def get_placeholders(self):
        """Parses sequence template and returns placeholder variables."""

        # Define regex
        regex = f'\{self.marker_string}([^$]+)\{self.marker_string}'

        found_placeholders = [match.group(1) for match in re.finditer(regex, self.raw_sequence)]

        # Check for duplicates
        for found_placeholder in found_placeholders:
            if found_placeholders.count(found_placeholder) != 1:

                error_msg = f"Placeholder {found_placeholder} found multiple times in sequence."
                self.hd.log.info(error_msg)

        # Remove duplicates from list
        found_placeholders = list(set(found_placeholders))

        return found_placeholders

    def prepend_sequence(self, string):
        self.sequence = string + self.sequence

    def is_ready(self):
        """ Return True if all placeholders have been replaced"""
        return len(self.unresolved_placeholders) == 0

    def __init__(self, hdawg_driver, sequence, placeholder_dict=None, waveform_dict=None, marker_string="$"):
        """ Initialize sequence with string

        :hdawg_driver: Instance of HDAWG_Driver
        :sequence: A string which contains sequence instructions,
            as defined in the ZI language seqc. This string can contain placeholders
            indicated by '$c$', where c is the name of the placeholder. The marker string $
            can be changed as an optional input parameter.
        :placeholder_dict: A dictionary of placeholder_names and values which need to be replaced
            before compilation of sequence. If for example '$c$' is included
            in the sequence string, 'c' is the name of the placeholder to be
            used as the dictionary key, while the value of the key is the value the placeholder will
            be replaced with in the sequence.
        :waveform_dict: Same as placeholder_dict, but values are numpy.arrays which will be tranformed to
        waveform commands.
        :marker_string: String wrapping placeholders in sequence_string.
        """

        # Store reference to HDAWG_Driver to use logging function.
        self.hd = hdawg_driver

        # Store raw sequence.
        self.raw_sequence = textwrap.dedent(sequence)

        # Store sequence with replaced placeholders.
        self.sequence = copy.deepcopy(self.raw_sequence)

        self.placeholder_dict = placeholder_dict
        self.waveform_dict = waveform_dict
        self.marker_string = marker_string

        # Retrieve placeholders in input sequence template
        self.placeholders = self.get_placeholders()

        # Keeps track of which placeholders has not been replaced yet.
        self.unresolved_placeholders = set(copy.deepcopy(self.placeholders))

        if placeholder_dict is not None:
            # Some sanity checks.
            for placeholder in placeholder_dict.keys():
                if placeholder not in self.placeholders:
                    error_msg = f"The placeholder {placeholder} cannot \
                        be found in the sequence."
                    hdawg_driver.log.error(error_msg)

            # Replace placeholders.
            self.replace_placeholders(self.placeholder_dict)

        if waveform_dict is not None:
            # Some sanity checks.
            for waveform in waveform_dict.keys():
                if waveform not in self.placeholders:
                    error_msg = f"The placeholder {error_msg} cannot \
                        be found in the sequence."
                    hdawg_driver.log.error(error_msg)

            # Replace waveforms
            self.replace_waveforms(self.waveform_dict)
