# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware class
for the Zurich Instruments HDAWG.
"""

import zhinst.utils
import re
import time
import textwrap
import copy

from pylabnet.utils.logging.logger import LogHandler

from pylabnet.utils.decorators.logging_redirector import log_standard_output


class HDAWGDriver():

    def disable_everything(self):
        """ Create a base configuration.
        Disable all available outputs, awgs, demods, scopes, etc.
        """
        zhinst.utils.disable_everything(self.daq, self.device_id)
        self.log.info("Disabled all wave outputs.")

    @log_standard_output
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

    def __init__(self, device_id, logger, api_level=6):
        """ Instantiate AWG

        :logger: instance of LogClient class
        :device_id: Device id of connceted ZI HDAWG, for example 'dev8060'
        :api_level: API level of zhins API
        """

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Part of this code has been modified from
        # ZI's Zurich Instruments LabOne Python API Example

        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate
        # with devices via the data server.
        # - the device ID string that specifies the device
        # branch in the server's node hierarchy.
        # - the device's discovery properties.

        err_msg = "This example can only be ran on an HDAWG."

        # Connect to device and log print output, not the lambda expression.
        (daq, device, props) = self.log_stdout(
            lambda: zhinst.utils.create_api_session(
                device_id,
                api_level,
                required_devtype='HDAWG',
                required_err_msg=err_msg
            )
        )

        self.log_stdout(lambda: zhinst.utils.api_server_version_check(daq))

        self.daq = daq
        self.device_id = device

        # Create a base configuration
        self.disable_everything()

        # read out number of channels from property dictionary
        self.num_outputs = int(
            re.compile('HDAWG(4|8{1})').match(props['devicetype']).group(1)
        )

    @log_standard_output
    def seti(self, node, new_int):
        """
        Warapper for daq.setInt commands. For instance, instead of
        daq.setInt('/dev8040/sigouts/0/on', 1), write

        hdawg.seti('sigouts/0/on, 1)

        :node: Node which will be appended to '/device_id/'
        :new_int: New value for integer
        """

        self.daq.setInt(f'/{self.device_id}/{node}', new_int)

    @log_standard_output
    def setd(self, node, new_double):
        """
        Warapper for daq.setDouble commands. For instance, instead of
        daq.setDouble('/dev8040/sigouts/0/range', 0.8), write

        hdawg.setd('sigouts/0/range')

        :node: Node which will be appended to '/device_id/'
        :new_double: New value for double.
        """

        self.daq.setDouble(f'/{self.device_id}/{node}', new_double)

    @log_standard_output
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
    def geti(self, node):
        """
        Warapper for daq.getInt commands. For instance, instead of
        daq.getInt('/dev8040/sigouts/0/busy'), write

        hdawg.geti('sigouts/0/busy')

        :node: Node which will be appended to '/device_id/'
        """

        return self.daq.getInt(f'/{self.device_id}/{node}')

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

    def enable_output(self, output_indices):
        """
        Enables wave output.

        Channel designation uses channel index (0 to 7),
        not channel number (1 to 8).

        :output_index: List or int containing
            integers indicating wave output 0 to 7
        """

        self._toggle_output(output_indices, 1)

    def disable_output(self, output_indices):
        """
        Disables wave output.

        :output_index: List or int containing
            integers indicating wave output 0 to 7
        """
        self._toggle_output(output_indices, 0)

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
                        f"Changed range of wave output {output_index} \
                            to {output_range} V."
                    )
            else:
                self.log.error(
                    f"Range {output_range} is not valid, allowed \
                        values for range are {allowed_ranges}"
                )
        else:
            self.log.error(
                f"This device has only {self.num_outputs} channels, \
                    channel index {output_index} is invalid."
            )


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

    def set_sampling_rate(self, sampling_rate_index):
        """ Set sampling rate of AWG output

        :sampling_rate_index: Index from 0 to 13, with the following mapping
            0 : 2.4GHz
            1 : 1.2 GHz
            ...
            13: 292.96 kHz
            See full table in LabOne Webpage.
        """

        if sampling_rate_index not in range(14):
            self.hd.log.error(
                f"Index {sampling_rate_index} not in \
                    permissible range {list(range(14))}."
            )
            return

        self.hd.seti(f'awgs/{self.index}/time', sampling_rate_index)
        self.hd.log.info(
            f"AWG {self.index}: Changed sampling rate \
                 to index {sampling_rate_index}."
        )

    def start(self):
        """ Start AWG"""
        self.module.set('awg/enable', 1)
        self.hd.log.info(f"AWG {self.index}: Started.")

    def stop(self):
        """ Start AWG"""
        self.module.set('awg/enable', 0)
        self.hd.log.info(f"AWG {self.index}: Stopped.")

    def compile_upload_sequence(self, sequence):
        """ Compile and upload AWG sequence to AWG Module

        :awgModule: Instance of AWGModule class.
        """

        # First check if all values have been replaced in sequence:
        if not sequence.is_ready():
            self.log.error("Sequence is not ready:\
                 Not all placeholders have been replaced.")
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

        if self.module.getInt('compiler/status') == 0:
            self.hd.log.info(
                "Compilation successful with no warnings, \
                     will upload the program to the instrument."
            )
        if self.module.getInt('compiler/status') == 2:
            self.hd.log.warn(
                "Compilation successful with warnings, \
                    will upload the program to the instrument."
            )
            self.hd.log.warn(
                f"Compiler warning: \
                     {self.module.getString('compiler/statusstring')}"
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
            self.hd.log.warning("Upload to the instrument failed.")

    def dyn_waveform_upload(self, index, waveform1, waveform2=None):
        """ Dynamically upload a numpy array into HDAWG Memory

        This will overwrite the allocated waveform memory of a waveform
        defined in the sequence. The index designates which waveform to
        overwrite:
        Let N be the total number of waveforms and M>0 be the number of
        waveforms defined from CSV files. Then the index
        of the waveform to be replaced is defined as following:
        - 0,...,M-1 for all waveforms defined from CSV file
            alphabetically ordered by filename,
        - M,...,N-1 in the order that the waveforms are
            defined in the sequencer program.
        For the case of M=0, the index is defined as:
        - 0,...,N-1 in the order that the waveforms are
            defined in the sequencer program.

        :waveform1: np.array containing waveform
        :waveform2: np.array containing waveform of second waveform is dynamic
            waveform upload is used for playback of two waveforms at two channels,
            as represented in the .seqc command `playWave(waveform1, waveform2)
        :index: Index of waveform to be overwritten as defined above
        """

        waveform_native = zhinst.utils.convert_awg_waveform(
            waveform1,
            waveform2
        )

        awg_index = self.module.get('index')['index'][0]
        self.hd.setv(
            f'awgs/{awg_index}/waveform/waves/{index}', waveform_native
        )


class Sequence():
    """ Helper class containing .seqc sequences and helper functions

    """

    def replace_placeholder(self, placeholder, value):
        """ Replace a placeholder by some value

        :placeholder: Placeholder string to be replaced.
        :value: Value to which the placeholder string need to be set.
        """
        self.sequence = self.sequence.replace(f"_{placeholder}_", str(value))
        self.unresolved_placeholders.remove(placeholder)

    def replace_waveform(self, placeholder, waveform):
        """ Replace a placeholder by a waveform

        :placeholder: Placeholder string to be replaced.
        :waveform: Numpy array designating the waveform.
        """
        waveform = 'vect(' + ','.join([str(x) for x in waveform]) + ')'
        self.sequence = self.sequence.replace(f"_{placeholder}_", waveform)
        self.unresolved_placeholders.remove(placeholder)

    def is_ready(self):
        """ Return True if all placeholders have been replaced"""
        return len(self.unresolved_placeholders) == 0

    def __init__(self, hdawg_driver, sequence, placeholders=None):
        """ Initialize sequence with string

        :hdawg_driver: Instance of HDAWG_Driver
        :sequence: A string containing a valid .seqc sequence,
            with possible palceholders
        :placeholders: A list of placeholder which need to be replaced
            before compilation of sequence.

        Note: A placeholder 'c' need to be included in a sequence as '_c_'
        """

        # Store reference to HDAWG_Driver to use logging function.
        self.hd = hdawg_driver

        # Some sanity checks.
        for placeholder in placeholders:
            if f"_{placeholder}_" not in sequence:
                error_msg = f"The placeholder _{placeholder}_ cannot \
                    be found in the sequence."
                hdawg_driver.log.error(error_msg)
                raise Exception(error_msg)

        # Store sequence and placeholders.
        self.sequence = textwrap.dedent(sequence)
        self.placeholders = placeholders
        # Keeps track of which placeholders has not been replaced yet.
        self.unresolved_placeholders = copy.deepcopy(placeholders)
