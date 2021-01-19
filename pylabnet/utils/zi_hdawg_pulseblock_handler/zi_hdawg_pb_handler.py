
import numpy as np
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.utils.pulseblock.pulse import PFalse


# Sampling rate of HDWAG sequencer (300 MHz).
SEQ_SAMP_RATE = 300e6

# Duration of setDIO() commands to be used as offset in wait() commands.
SETDIO_OFFSET = 4


class DIOPulseBlockHandler():

    def __init__(self, pb, assignment_dict=None, samp_rate=SEQ_SAMP_RATE, hd=None, end_low=True):
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

            The assignment dictionary can be incomplete,
            in which case the user will be asked to provide the
            missing values. If no assignment dictionary is
            provided, user is asked to provide all DIO bit values.

        :end_low: (bool) whether or not to force the sequence to end low
        """

        # Use the log client of the HDAWG.
        self.hd = hd
        self.log = hd.log
        self.sr = samp_rate

        # Store arguments.
        self.pb = pb

        # Handle end low case
        self.end_low = end_low

        # Ask user for bit assignment if no dictionary provided.
        if assignment_dict is None:

            # Initiate empty dictionary
            self.assignment_dict = {}

            # Ask user to assign all channels
            self._aks_for_dio_assignment(self.pb.p_dict.keys())

        # Store assignment dict if provided.
        else:
            self.assignment_dict = assignment_dict

            # Check key value integrity of assignment dict.
            self._check_key_assignments()

        self.DIO_bits = self.assignment_dict.values()

        # Store remapped samples, number of samples and number of traces.
        self.sample_dict, self.num_samples, self.num_traces = self._get_remapped_samples(samp_rate=samp_rate)

    def _aks_for_dio_assignment(self, keys_to_assign):
        """Ask user to provide DIO bit for trace

        :keys_to_assign: (np.array) Array of keys in pulseblock dictionary
            (trace names).
        """

        for trace_name in keys_to_assign:
            dio_bit = input(f"Please assign a DIO bit (0-31) to pulse trace '{trace_name}':")

            # Check if user has entered a int.
            wrong_int_msg = "Please enter an integer from 0-31."
            try:
                dio_bit = int(dio_bit)
            except ValueError:
                self.log.error(wrong_int_msg)

            if dio_bit not in range(32):
                self.log.error(wrong_int_msg)

            # Check if DIO bit is already assigned
            if dio_bit in self.assignment_dict.values():
                self.log.error(f"DIO bit is {dio_bit} already in use.")

            self.assignment_dict[trace_name] = dio_bit

    def _check_key_assignments(self):
        """Check if key values in assignment dict coincide with keys in pulseblock"""

        if not self.assignment_dict.keys() == self.pb.p_dict.keys():
            for pb_key in self.pb.p_dict.keys():
                if pb_key not in self.assignment_dict.keys():
                    self.log.warn(
                        f"Key '{pb_key}' in pulseblock instance not found in assignment dictionary, please specify."
                    )

                    # Ask user to provide DIO bit for key.
                    self._aks_for_dio_assignment([pb_key])

    def _get_remapped_samples(self, samp_rate):
        """Transforms pulsblock object into dictionary of sample-wise defined digital waveforms.

        :samp_rate: (float) Sampling rate of HDAWG sequencer
        Returns dictionary with keys corresponding to DIO bit numbers and
        values to the desired digital waveform.
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
        """Generate array of DIO codewords.

        Given the remapped sample array, translate it into an
        array of DIO codewords, sample by sample.
        """

        dio_bits = self.sample_dict.keys()

        # Array storing one codeword per sample.
        dio_codewords = np.zeros(self.num_samples, dtype='int64')

        for sample_num in range(self.num_samples):

            # Initial codeword: 00000 ... 0000
            codeword = 0b0

            for dio_bit in dio_bits:

                sample_val = self.sample_dict[dio_bit][sample_num]

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

    def zip_dio_commands(self, dio_codewords):
        """Generate zipped version of DIO commands.

        This will reduce the digital waveform to
        specify the times, when the DIO output changes, and
        corresponsing waittimes in between.

        :wait_offest: (int) Number of samples to adjust the waittime in order to
            account for duration of setDIO() command.
        """

        # Find out where the the codewords changes.
        dio_change_index = np.where(dio_codewords[:-1] != dio_codewords[1:])[0]

        # Use difference of array to get waittimes,
        # prepend first sample, append the waittime to match sequence length.
        num_samples = len(dio_codewords)
        waittimes = np.concatenate(
            [
                [dio_change_index[0]],
                np.diff(dio_change_index),
                [num_samples - dio_change_index[-1]]
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

    def construct_dio_sequence(self, codewords, reduced_codewords, waittimes, wait_offset=SETDIO_OFFSET):
        """Construct .seqc sequence representing digital waveform

        This function also checks if the initial waveform can be reconstructed by the
        reduced codewords and the waittimes.

        :codewords: (np.array) The full, sample-by-sample array of DIO codewords
            representing the waveform.
        :reduced_codewords: (np.array) Array of unique codewords
            (without repetitions) played back, in sequential order.
        :waittimes: (np.array) Array of waittimes between setDIO() commands,
            in sequential order.
        :wait_offset: (int) Number of samples to adjust the waittime in order to
            account for duration of setDIO() command.
        """

        waveform = np.zeros(np.sum(waittimes), dtype='int64')
        waveform[0] = reduced_codewords[0]

        sequence = ""
        set_dio_raw = "setDIO(_d_);"
        wait_raw = "wait(_w_);"

        for i, waittime in enumerate(waittimes):
            summed_waittime = np.sum(waittimes[0:i]) + 1
            waveform[summed_waittime:summed_waittime+waittime] = reduced_codewords[i]

            # Add setDIO command to sequence
            sequence += set_dio_raw.replace("_d_", str(int(reduced_codewords[i])))

            # Add waittime to sequence
            sequence += wait_raw.replace("_w_", str(int(max(waittime-wait_offset, 0))))

        # Sanity check if waveform is reproducible from reduced codewords and waittimes.
        if not (codewords == waveform).all():
            self.log.error("Cannot reconstruct digital waveform from codewords and waittimes.")

        # Add setDIO(0); to end if selected.
        if self.end_low:
            # Add 0 waittime to sequence
            sequence += set_dio_raw.replace("_d_", '0')

        return sequence

    def get_dio_sequence(self):
        """Generate a set of .seqc instructions for digital waveform

        Returns a string containing a series of setDIO() and wait() .seqc
        commands which will reproduce the waveform defined
        by the pulseblock object.
        """

        # Get sample-wise sets of codewords.
        codewords = self.gen_codewords()

        # Reduce this array to a set of codewords + waittimes.
        reduced_codewords, waittimes = self.zip_dio_commands(codewords)

        # Reconstruct set of .seqc instructions representing the digital waveform.
        sequence = self.construct_dio_sequence(
            codewords=codewords,
            reduced_codewords=reduced_codewords,
            waittimes=waittimes
        )

        return sequence

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
