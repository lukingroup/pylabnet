# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware class for the Zurich Instruments HDAWG.
"""

import zhinst.utils
import re
import time

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase

from pylabnet.utils.decorators.logging_redirector import log_standard_output


class HDAWG_Driver():

    def disable_everything(self):
        """ Create a base configuration: Disable all available outputs, awgs, demods, scopes,.. """
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

        # Part of this code has been modified from ZI's Zurich Instruments LabOne Python API Example

        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate with devices via the data server.
        # - the device ID string that specifies the device branch in the server's node hierarchy.
        # - the device's discovery properties.

        err_msg = "This example can only be ran on an HDAWG."

        # Connect to device and log print output, not the lambda expression.
        (daq, device, props) = self.log_stdout(lambda: zhinst.utils.create_api_session(device_id, api_level, required_devtype='HDAWG',
                                                required_err_msg=err_msg))

        self.log_stdout(lambda: zhinst.utils.api_server_version_check(daq))

        self.daq = daq
        self.device_id = device

        # Create a base configuration: Disable all available outputs, awgs, demods, scopes,...
        self.disable_everything()

        # read out number of channels from property dictionary
        self.num_outputs = int(re.compile('HDAWG(4|8{1})').match(props['devicetype']).group(1))

    @log_standard_output
    def seti(self, node, new_int):
        """
        Warapper for daq.setInt commands. For instance, instead of
        daq.setInt('/dev8040/sigouts/0/on', 1), write

        hdawg.seti('sigouts/0/on, 1)

        :node: Node which will be appended to '/device_id/'
        :new_int: New value for integer
        """

        self.daq.setInt('/{device_id}/{node}'.format(device_id=self.device_id, node=node), new_int)

    @log_standard_output
    def setd(self, node, new_double):
        """
        Warapper for daq.setDouble commands. For instance, instead of
        daq.setDouble('/dev8040/sigouts/0/range', 0.8), write

        hdawg.setd('sigouts/0/range')

        :node: Node which will be appended to '/device_id/'
        :new_double: New value for double.
        """

        self.daq.setDouble('/{device_id}/{node}'.format(device_id=self.device_id, node=node), new_double)

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
                self.seti('sigouts/{output_index}/on'.format(output_index=output_index), target_index)
                if target_index == 1:
                    self.log.info("Enabled wave output {}.".format(output_index))
                elif target_index == 0:
                    self.log.info("Disable wave output {}.".format(output_index))
            else:
                self.log.error(f"This device has only {self.num_outputs} channels, channel index {output_index} is invalid.")

    def enable_output(self, output_indices):
        """
        Enables wave output.

        Channel designation uses channel index (0 to 7),
        not channel number (1 to 8).

        :output_index: List or int containing integers indicating wave output 0 to 7
        """

        self._toggle_output(output_indices, 1)

    def disable_output(self, output_indices):
        """
        Disables wave output.

        :output_index: List or int containing integers indicating wave output 0 to 7
        """
        self._toggle_output(output_indices, 0)

    def set_output_range(self, output_index, output_range):
        """
        Set the output range.

        :output_index: List or int containing integers indicating wave output 0 to 7
        :output_range: Double indicating the range of wave output, in Volt.
            All waveforms (ranging from 0 to 1 in value) will be multiplied with this value. Possible ranges are:
            0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5 (V)
        """

        allowed_ranges = [0.2, 0.4, 0.6, 0.8, 1, 2, 3, 4, 5]

        if output_index in range(self.num_outputs):
            if output_range in allowed_ranges:

                # Send change range command.
                self.setd('sigouts/{output_index}/range'.format(output_index=output_index), output_range)

                # Wait for HDAWG to be ready, try 100 times before timeout.
                max_tries = 100
                num_tries = 0
                while self.geti(f'sigouts/{output_index}/busy') and num_tries < max_tries:
                    time.sleep(0.2)
                    num_tries += 1

                if num_tries is max_tries:
                    self.log.error(f"Range change timeout after {max_tries} tries.")
                else:
                    self.log.info(f"Changed range of wave output {output_index} to {output_range} V.")
            else:
                self.log.error(f"Range {output_range} is not valid, allowed values for range are {allowed_ranges}")
        else:
            self.log.error(f"This device has only {self.num_outputs} channels, channel index {output_index} is invalid.")

    def setup_awg_module(self, index):
        """ Startup helper for awg module

        :index: Which AWG sequencer to be used
            0 - 3 for 4x2 channel grouping
            0 - 1 for 2x4 channel grouping
            0     for 1x8 channel grouping

        Returns instance ow awgModule
        """

        # Check if chosen index is allowed for current channel grouping.
        channel_grouping = self.geti('system/awg/channelgrouping')

        if channel_grouping == 0:
            num_awgs = 4
        elif channel_grouping == 1:
            num_awgs = 2
        elif channel_grouping == 2:
            num_awgs = 1

        allowed_indices = range(num_awgs)

        if index not in allowed_indices:
            self.log.error(f"Current channel grouping only allows for the following AWG indices {list(allowed_indices)}")
            return None

        # Create an instance of the AWG Module
        awgModule = self.daq.awgModule()
        awgModule.set('index', index)
        awgModule.set('device', self.device_id)
        awgModule.execute()

        return awgModule

    def compile_upload_sequence(self, awgModule, sequence):
        """ Compile and upload AWG sequence to AWG Module

        :awgModule: Instance of awgModule.
        :sequence: Valid .seqc sequence to be uploaded.
        """

        awgModule.set('compiler/sourcestring', sequence)
        # Note: when using an AWG program from a source file (and only then), the compiler needs to
        # be started explicitly with awgModule.set('compiler/start', 1)
        while awgModule.getInt('compiler/status') == -1:
            time.sleep(0.1)

        if awgModule.getInt('compiler/status') == 1:
            # compilation failed, raise an exception
            self.log.warning(awgModule.getString('compiler/statusstring'))

        if awgModule.getInt('compiler/status') == 0:
            self.log.info("Compilation successful with no warnings, will upload the program to the instrument.")
        if awgModule.getInt('compiler/status') == 2:
            self.log.warning("Compilation successful with warnings, will upload the program to the instrument.")
            self.log.warning("Compiler warning: ", awgModule.getString('compiler/statusstring'))

        # Wait for the waveform upload to finish
        time.sleep(0.2)
        i = 0
        while (awgModule.getDouble('progress') < 1.0) and (awgModule.getInt('elf/status') != 1):
            self.log.info("{} progress: {:.2f}".format(i, awgModule.getDouble('progress')))
            time.sleep(0.2)
            i += 1
        self.log.info("{} progress: {:.2f}".format(i, awgModule.getDouble('progress')))
        if awgModule.getInt('elf/status') == 0:
            self.log.info("Upload to the instrument successful.")
        if awgModule.getInt('elf/status') == 1:
            self.log.warning("Upload to the instrument failed.")