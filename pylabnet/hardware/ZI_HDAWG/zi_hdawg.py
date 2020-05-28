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

# Storing the sampling rates and the corresponding target integers for the setInt command
SAMPLING_RATE_DICT = {
    '2.4 GHz':       0,
    '1.2 GHz':       1,
    '600 MHz':       2,
    '300 MHz':       3,
    '150 MHz':       4,
    '75 MHz':        5,
    '37.5 MHz':      6,
    '18.75 MHz':     7,
    '9.37 MHz':      8,
    '4.68 MHz':      9,
    '2.34 MHz':      10,
    '1.17 MHz':      11,
    '585.93 kHz':    12,
    '292.96 kHz':    13,
}


class Driver():

    def reset_DIO_outputs(self):
        """Sets all DIO outputs to low"""
        self.seti('dios/0/output', 0)
        self.log.info("Set all DIO outputs to low.")

    def disable_everything(self):
        """ Create a base configuration.
        Disable all available outputs, awgs, demods, scopes, etc.
        """
        zhinst.utils.disable_everything(self.daq, self.device_id)
        self.log.info("Disabled everything.")

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

        err_msg = "This example can only be run on an HDAWG."

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
        self.reset_DIO_outputs()

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

    def start(self):
        """ Start AWG"""
        self.module.set('awg/enable', 1)
        self.hd.log.info(f"AWG {self.index}: Started.")

    def stop(self):
        """ Stop AWG"""
        self.module.set('awg/enable', 0)
        self.hd.log.info(f"AWG {self.index}: Stopped.")

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
        :sequence: A string which contains sequence instructions,
            as defined in the ZI language seqc. This string can contain placeholders
            indicated by '_c_', where c is the name of the placeholder.
        :placeholders: A list of placeholders which need to be replaced
            before compilation of sequence. If for example '_c_' is included
            in the sequence string, 'c' is the name of the placeholder to be
            passed in this argument.
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

import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
import numpy as np
#from pylabnet.pulseblock.pb_iplot import iplot
from pylabnet.utils.pulseblock.pb_sample import pb_sample

class DIOPulseBlockHandler():

    def __init__(self, pb, assignment_dict, samp_rate=300e6, hd=None):
        """ Initializes the pulse block handler for DIO

        :hd: (object) And instance of the zi_hdawg.Driver()
        :pb: (object) An instance of a pb.PulseBlock()
        :samp_rate: (float) Sampling rate of HDAWG sequencer (300 MHz)

        :assignment_dict: (dictionary) Dictionary mapping the channel names in the
            pulse block to DIO channels. e.g.
            {
                'mw_gate' : 1,
                'ctr' : 2
            }
            assigns the channel mw_gate to DIO bit 1, etc.
        """

        self.hd = hd
        self.pb = pb
        self.assignment_dict = assignment_dict

        self.DIO_bits = assignment_dict.values()

        # Read in remapped samples
        self.sample_dict, self.num_samples, self.num_traces = self._get_remapped_samples(samp_rate=samp_rate)

        # TODO implement some error checking,
        # e.g. check if number of traces and
        # number if entries in assignment_dict coincide.


    def _get_remapped_samples(self, samp_rate):
        """ Get sample dictionary

        :samp_rate: (float) Sampling rate of HDAWG DIO (50 MHz)

        Returnes dictionary with keys corresponding to DIO bit numbers and
        values to the desired digital waveform
        """

        # Turn pulse block into sample dictionary
        sampled_pb = pb_sample(self.pb, samp_rate=samp_rate)

        # Number of samples per pulse
        num_samples = sampled_pb[-2]
        traces = sampled_pb[0]

        # Number of different traces
        num_traces = len(traces)

        # Create dictionary with channel names replaces by DIO bit
        sample_dict = {}
        for channel_name in traces.keys():
            sample_dict.update(
                {self.assignment_dict[channel_name]: traces[channel_name]}
            )

        return sample_dict, num_samples, num_traces

    def gen_codewords(self):
        """Generate array of DIO codewords

        Given the remapped sample array, translate it into an
        array of DIO codewords.
        """

        # # Combine samples array into one 2D array.
        # combined_samples = np.zeros((self.num_traces, self.num_samples))
        # for i in range(self.num_traces):
        #     combined_samples[i:] = self.sample_dict[i]

        dio_bits = self.sample_dict.keys()

        # Array storing one codeword per sample.
        self.dio_codewords = np.zeros(self.num_samples, dtype='int64')

        for sample_num in range(self.num_samples):

            # Initial codeword: 00000 ... 0000
            codeword = 0b0

            for dio_bit in dio_bits:

                sample_val = self.sample_dict[dio_bit][sample_num]

                # If value is True, add 1 at  dio_bit-th position
                if sample_val:

                    # E.g., for DIO-bit 3: 0000 ... 0001000
                    bitshifted_dio_bit = (0b1 << int(dio_bit))

                 # If value is False, do nothing.
                else:
                    bitshifted_dio_bit = 0b0

                # Binary OR updates codeword.
                codeword = codeword | bitshifted_dio_bit

            # Store codeword.
            self.dio_codewords[sample_num] = codeword

    def prepare_DIO_sequence(self):

        raw_snippet = "setDIO(_d_);"
        self.seq_c_codeword = ""

        for codeword in self.dio_codewords:
            self.seq_c_codeword = self.seq_c_codeword + raw_snippet.replace("_d_", str(int(codeword)))

        self.seq_c_codeword


    def reconstruct_dio_waveform(self, waittimes, dio_vals, wait_offset):

        waveform = np.zeros(np.sum(waittimes), dtype='int64')
        waveform[0] = dio_vals[0]

        sequence = ""
        set_dio_raw = "setDIO(_d_);"
        wait_raw = "wait(_w_);"


        for i, waittime in enumerate(waittimes):
            summed_waittime = np.sum(waittimes[0:i]) + 1
            waveform[summed_waittime:summed_waittime+waittime] = dio_vals[i]

            # Add setDIO command to sequence
            sequence += set_dio_raw.replace("_d_", str(int(dio_vals[i])))

            # Add waittime to sequence
            sequence += wait_raw.replace("_w_", str(int(max(waittime-wait_offset, 0))))

        return waveform, sequence

        waveform = np.zeros()
    def zip_dio_commands(self, wait_offset=4):
        """Generate zipped version of DIO commands.

        This will reduce the digital waveform to
        specify the times, when the DIO output changes, and
        corresponsing waittimes in between.

        :wait_offest: (int) How much to offset the waittimes in order to account for
            execution times of the setDIO command (calibrated to 4 samples)
        """

        # Find out where the the codewords change:
        dio_change_index = np.where(self.dio_codewords[:-1] != self.dio_codewords[1:])[0]

        # Use difference of array to get waittimes, prepend first sample, append the waittime to match sequence length.

        num_samples = len(self.dio_codewords)

        waittimes = np.concatenate([[dio_change_index[0]], np.diff(dio_change_index), [num_samples - dio_change_index[-1]]])

        assert sum(waittimes) == num_samples, "Mismatch between sum of waittimes and waveform length."

        # Store DIO values occuring after state change
        dio_vals = np.concatenate([[self.dio_codewords[0]], self.dio_codewords[dio_change_index+1]])

        rec_waveform, sequence = self.reconstruct_dio_waveform(waittimes, dio_vals, wait_offset)

        # Sanity check if waveform is reproducable using dio vals and waittimes
        assert (self.dio_codewords == rec_waveform).all()

        return sequence

    def setup_hd(self):

        # Read in current configuration of DIO-bus.
        current_config = self.hd.geti('dios/0/drive')

        for DIO_bit in self.DIO_bits:
            if DIO_bit in range(8):
                toggle_bit = 1  # 1000
            elif DIO_bit in range(8, 16):
                toggle_bit = 2  # 0100
            elif DIO_bit in range(16, 24):
                toggle_bit = 4  # 0010
            elif DIO_bit in range(24, 32):
                toggle_bit = 8  # 0001
            else:
                self.log.error(f"DIO_bit {DIO_bit} invalid, must be in range 0-31.")

            # Set new configuration by using the bitwise OR.
            new_config = current_config | toggle_bit
            self.hd.seti('dios/0/drive', new_config)

            # Update current configuration
            current_config = new_config


def main():

    def rabi_element(tau=0, aom_offset=0):
        rabi_element = pb.PulseBlock(
            p_obj_list=[
                po.PTrue(ch='aom', dur=1.1e-6),
                po.PTrue(ch='ctr', t0=0.5e-6, dur=0.5e-6)
            ]
        )
        temp_t = rabi_element.dur

        rabi_element.insert(
            p_obj=po.PTrue(ch='mw_gate', dur=tau, t0=temp_t+0.7e-6)
        )
        temp_t = rabi_element.dur

        rabi_element.insert(
            p_obj=po.PTrue(ch='aom', t0=temp_t+aom_offset, dur=2e-6)
        )
        rabi_element.insert(
            p_obj=po.PTrue(ch='ctr', t0=temp_t, dur=0.5e-6)
        )

        rabi_element.dflt_dict = dict(
            aom=po.DFalse(),
            ctr=po.DFalse(),
            mw_gate=po.DFalse()
        )

        return rabi_element

    rabi_pulseblock = rabi_element(1000e-9)

    as_dict = {
        'mw_gate':   1,
        'ctr':      17,
        'aom':      31,

    }

    dev_id = 'dev8040'
    from pylabnet.utils.logging.logger import LogClient

    # Instantiate
    logger = LogClient(
        host='192.168.1.2',
        port=2056,
        module_tag=f'ZI HDAWG {dev_id}'
    )

    hd = Driver(dev_id, logger=logger)
    pb_handler = DIOPulseBlockHandler(rabi_pulseblock, as_dict, hd=hd)
    pb_handler.setup_hd()
    pb_handler.gen_codewords()
    pb_handler.zip_dio_commands()
    pb_handler.prepare_DIO_sequence()
    #pb_handler.prepare_dio_settings()





if __name__ == "__main__":
    main()