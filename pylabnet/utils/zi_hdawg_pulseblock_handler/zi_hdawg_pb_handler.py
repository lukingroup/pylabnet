import numpy as np
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.utils.pulseblock.pulse import PFalse


# Sampling rate of HDWAG sequencer (300 MHz).
SEQ_SAMP_RATE = 300e6

# Duration of setDIO() commands to be used as offset in wait() commands.
SETDIO_OFFSET = 4


class AWGPulseBlockHandler():

    def __init__(self, pb, assignment_dict=None, exp_config_dict=None,
                 samp_rate=SEQ_SAMP_RATE,  hd=None, end_low=True):
        """ Initializes the pulse block handler for the ZI HDAWG.

        :hd: (object) And instance of the zi_hdawg.Driver()
        :pb: (object) An instance of a pb.PulseBlock()
        :samp_rate: (float) Sampling rate of HDAWG sequencer (300 MHz)

        :assignment_dict: (dictionary) Dictionary mapping the channel names in the
            pulse block to DIO bits or analog channels. e.g.
            {
                "mw_gate" : ["dio", 0],
                "ctr" : ["dio", 1],
                "laser" : ["analog", 7],
            }

            The assignment dictionary can be incomplete,
            in which case the user will be asked to provide the
            missing values. If no assignment dictionary is
            provided, user is asked to provide all channel values.
        :exp_config_dict: (dict) Dictionary of any experiment configurations.
        :end_low: (bool) whether or not to force the sequence to end low
        """

        # Use the log client of the HDAWG.
        self.hd = hd
        self.log = hd.log

        # Store arguments.
        self.pb = pb

        # Handle end low case
        self.end_low = end_low

        self.sr = samp_rate
        self.exp_config_dict = exp_config_dict        

        # Ask user for bit assignment if no dictionary provided.
        if assignment_dict is None:
            # Initiate empty dictionary
            self.assignment_dict = {}
            # Ask user to assign all channels
            self._ask_for_ch_assignment(self.pb.p_dict.keys())

        # Store assignment dict if provided.
        else:
            self.assignment_dict = assignment_dict
            # Check key value integrity of assignment dict.
            self._check_key_assignments()

        self.DIO_bits = [value[1] for value in self.assignment_dict.values() if value[0] == "dio"]
        self.analog_chs = [value[1] for value in self.assignment_dict.values() if value[0] == "analog"]

        # Store remapped samples, number of samples and number of traces for the
        # digital channels.
        self.digital_sample_dict, self.num_digital_samples, self.num_digital_traces = self._get_remapped_digital_samples(samp_rate=samp_rate)

    def _ask_for_ch_assignment(self, keys_to_assign):
        """Ask user to provide bit/channel number for trace

        :keys_to_assign: (np.array) Array of keys in pulseblock dictionary
            (trace names).
        """

        for trace_name in keys_to_assign:

            if trace_name.is_analog:
                ch_num = input(f"Please assign an analog channel (0-7) to pulse trace '{trace_name.name}':")

                # Check if user has entered a int.
                wrong_int_msg = "Please enter an integer from 0-7."
                try:
                    ch_num = int(ch_num)
                except ValueError:
                    self.log.error(wrong_int_msg)

                if ch_num not in range(8):
                    self.log.error(wrong_int_msg)

            else:
                ch_num = input(f"Please assign a DIO bit (0-31) to pulse trace '{trace_name.name}':")

                # Check if user has entered a int.
                wrong_int_msg = "Please enter an integer from 0-31."
                try:
                    ch_num = int(ch_num)
                except ValueError:
                    self.log.error(wrong_int_msg)

                if ch_num not in range(32):
                    self.log.error(wrong_int_msg)

            # Check if channel is already assigned
            if ch_num in self.assignment_dict.values():
                self.log.error(f"DIO bit / Channel {ch_num} already in use.")

            # assignment_dict items are in the form (analog/digital, channel)
            self.assignment_dict[trace_name][0] = "analog" if trace_name.is_analog else "dio"
            self.assignment_dict[trace_name][1] = ch_num

    def _check_key_assignments(self):
        """Check if key values in assignment dict coincide with keys in pulseblock"""

        for pb_key in self.pb.p_dict.keys():
            if pb_key.name not in self.assignment_dict.keys():
                self.log.warn(
                    f"Key '{pb_key.name}' in pulseblock instance not found in assignment dictionary, please specify."
                )

                # Ask user to provide channel number for key.
                self._ask_for_ch_assignment([pb_key])

    def _get_remapped_digital_samples(self, samp_rate):
        """Transforms pulseblock object into dictionary of sample-wise defined digital waveforms.

        :samp_rate: (float) Sampling rate of HDAWG sequencer
        Returns dictionary with keys corresponding to DIO bit numbers and
        values to the desired digital waveform.
        """

        # Turn pulse block into sample dictionary
        sampled_digital_pb = pb_sample(self.pb, samp_rate=samp_rate)

        # Number of samples per pulse
        num_digital_samples = sampled_digital_pb[-2]
        traces = sampled_digital_pb[0]

        # Number of different traces
        num_digital_traces = len(traces)

        # Create dictionary with channel names replaced by DIO bit
        digital_sample_dict = {}
        for channel_name in traces.keys():
            digital_sample_dict.update(
                # assignment_dict items are in the form (analog/digital, channel)
                {self.assignment_dict[channel_name][1]: traces[channel_name]}
            )

        return digital_sample_dict, num_digital_samples, num_digital_traces

    def gen_digital_codewords(self):
        """Generate array of DIO codewords.

        Given the remapped sample array, translate it into an
        array of DIO codewords, sample by sample.
        """

        dio_bits = self.digital_sample_dict.keys()

        # Array storing one codeword per sample.
        dio_codewords = np.zeros(self.num_digital_samples, dtype='int64')

        for sample_num in range(self.num_digital_samples):

            # Initial codeword: 00000 ... 0000
            codeword = 0b0

            for dio_bit in dio_bits:

                sample_val = self.digital_sample_dict[dio_bit][sample_num]

                # If value is True, add 1 at dio_bit-th position
                if sample_val:

                    # E.g., for DIO-bit 3: 0000 ... 0001000
                    bitshifted_dio_bit = (0b1 << int(dio_bit))

                # If value is False, do nothing.
                else:
                    bitshifted_dio_bit = 0b0

                # Binary OR updates codeword.
                codeword = codeword | bitshifted_dio_bit

            # Store codeword.
            dio_codewords[sample_num] = codeword

        return dio_codewords
    
    def gen_analog_codewords(self):
        """Generate the codewords for the analog channels and the timestep in
        sample number that the codewords should be executed at.

        :return: analog_setup (str): AWG commands used for setup of the pulse
            sequence and will only need to be run once even if the sequence is 
            run multiple times.
        :return: analog_codewords (list of str tuples): List of analog codewords 
            to be placed inside the loop and run every iteration. The codewords  
            in each tuple should be run at the "same" timstep (up to the time 
            taken to run each command).
        :return: analog_times (list of int): List of time steps at which each 
            codeword tuple should be run.
        """
        # TODO YQ
        analog_setup, analog_codewords, analog_times = "", [], []
        

        return analog_setup, analog_codewords, analog_times

    def zip_digital_commands(self, dio_codewords): 
        """Generate zipped version of DIO commands.

        This will reduce the digital waveform to specify the times, when the DIO 
        output changes, and corresponsing waittimes in between. Does not 
        account for the time taken for the wait() command.

        :wait_offest: (int) Number of samples to adjust the waittime in order to
            account for duration of setDIO() command.
        """

        # Find out where the the codewords changes. The indices refer to the
        # left edge of transition, e.g. [0 0 1] returns index 1.
        dio_change_index = np.where(dio_codewords[:-1] != dio_codewords[1:])[0]

        # Use difference of array to get waittimes,
        # prepend first sample, append the waittime to match sequence length.
        # Add 1 for first wait time since we're measuring time between the left   
        # edge of transitions, the first transition "takes place" at index -1. 
        num_samples = len(dio_codewords)
        waittimes = np.concatenate(
            [
                [dio_change_index[0] + 1], 
                np.diff(dio_change_index),
                [(num_samples - 1) - dio_change_index[-1]]
            ]
        )

        if not sum(waittimes) == num_samples:
            self.log.error("Mismatch between sum of waittimes and waveform length.")

        # Store DIO values occuring after state change, prepend first codeword.
        reduced_codewords = np.concatenate(
            [
                [dio_codewords[0]],
                dio_codewords[dio_change_index+1]
            ]
        )

        return reduced_codewords, waittimes

    def combine_command_timings(self, reduced_digital_codewords, digital_waittimes, 
                                analog_codewords, analog_times):

        """ Combine the commands and timings from the analog and digital commands
        to give a combined list of codewords and wait time intervals. 

        :reduced_digital_codewords: (list of str) Array of unique digital 
            codewords in time order.
        :digital_waittimes: (list of int) Array of wait times between each 
            digital command.            
        :analog_codewords: (list of str tuples) Array of digital commands in 
            time order. Each entry is a tuple as there could be multiple comands 
            that need to be run at a given timestep.
        :analog_times: (list of int) Array of wait times between each analog 
            command.            
        """

        # TODO YQ
        combined_codewords, combined_waittimes  = reduced_digital_codewords, digital_waittimes

        return combined_codewords, combined_waittimes 

    # TODO YQ: THis will need to incorporate both the digital and analog reduced
    # TODO YQ: codewords and interleaved waittimes.
    def construct_awg_sequence(self, reduced_codewords, waittimes, wait_offset=SETDIO_OFFSET):
        """Construct .seqc sequence representing the AWG instructions to output
        a set of pulses over multiple channels

        :reduced_codewords: (list) Array of unique codewords
            (without repetitions) played back, in sequential order, from both
            digital and analog channels.
        :waittimes: (np.array) Array of waittimes between commands, in 
            sequential order.
        :wait_offset: (int) Number of samples to adjust the waittime in order to
            account for duration of setDIO() command.
        """

        waveform = np.zeros(np.sum(waittimes), dtype='int64')
        waveform[0] = reduced_codewords[0]

        sequence = ""
        set_dio_raw = "setDIO({});"
        wait_raw = "wait({});"

        if self.exp_config_dict["preserve_bits"]:
            # Read current output state of the DIO
            sequence += "var current_state = getDIO();" # TODO YQ: change to a correct way of reading current bits

            # Mask is 1 in the position of each used DIO bit
            mask  = sum(1 << bit for bit in self.digital_sample_dict.keys())
            sequence += f"var mask = {bin(mask)};" 

            # masked_state zeros out bits in the mask from the current_state
            sequence += "var masked_state = ~mask & current_state;"

        for i, waittime in enumerate(waittimes):

            # TODO: was used for previous redundant error checking. 
            # TODO: see if we can do something similar with the combined digital & analog codeword seqs
            # summed_waittime = np.sum(waittimes[0:i]) 
            # waveform[summed_waittime:summed_waittime+waittime] = reduced_codewords[i]

            # Add setDIO command to sequence
            dio_codeword = int(reduced_codewords[i])
            if self.exp_config_dict["preserve_bits"]:
                masked_codeword = (mask & dio_codeword) # Zero out any bits that fall outside the mask
                sequence += set_dio_raw.format(f"masked_state | {masked_codeword}")
            else:
                sequence += set_dio_raw.format(dio_codeword)

            # Add waittime to sequence. Prevent negative waittimes.
            sequence += wait_raw.format(int(max(waittime - wait_offset, 0)))

        # TODO: was used for previous redundant error checking. 
        # Sanity check if waveform is reproducible from reduced codewords and waittimes.
        # if not (codewords == waveform).all():
        #     self.log.error("Cannot reconstruct digital waveform from codewords and waittimes.")

        # Add setDIO(0); to end if selected.
        if self.end_low:
            if self.exp_config_dict["preserve_bits"]:
                sequence += set_dio_raw.format("masked_state")
            else:
                sequence += set_dio_raw.format("0")

        return sequence

    def get_awg_sequence(self):
        """Generate a set of .seqc instructions for the AWG to output a set of 
        pulses over multiple channels

        Returns a string containing a series of setDIO() and wait() .seqc
        commands which will reproduce the waveform defined
        by the pulseblock object.

        :return: setup_seq (str): AWG commands used for setup of the pulse
            sequence and will only need to be run once even if the sequence is 
            run multiple times.
        :return: sequence (str): AWG commands (e.g. setDIO() and wait()) that
            will generate the pulses described by the pulseblock.

        """

        # Get sample-wise sets of codewords for the digital channels.
        digital_codewords = self.gen_digital_codewords()

        # Reduce this array to a set of codewords + waittimes.
        reduced_digital_codewords, digital_waittimes = self.zip_digital_commands(digital_codewords)

        # Get codewords for the analog channels
        setup_seq, analog_codewords, analog_times = self.gen_analog_codewords()

        combined_codewords, combined_waittimes = self.combine_command_timings(
                                        reduced_digital_codewords, 
                                        digital_waittimes, 
                                        analog_codewords, 
                                        analog_times)

        # Reconstruct set of .seqc instructions representing the digital waveform.
        sequence = self.construct_awg_sequence(
            reduced_codewords=combined_codewords,
            waittimes=combined_waittimes,
        )

        return setup_seq, sequence

    def setup_hd(self):
        """Enable driving of DIO buses of relevant DIO bits."""

        # Set DIO mode to AWG sequencer
        self.hd.seti('dios/0/mode', 1)

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
                self.log.error(
                    f"DIO_bit {DIO_bit} invalid, must be in range 0-31."
                )

            # Set new configuration by using the bitwise OR.
            new_config = current_config | toggle_bit
            self.hd.seti('dios/0/drive', new_config)

            # Update current configuration
            current_config = new_config
