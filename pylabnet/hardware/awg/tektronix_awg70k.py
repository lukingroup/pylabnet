from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler
import numpy as np


class Driver:
    """Driver class for Ethernet controlled Tektronix 70001B AWG"""

    def __init__(self, ip_address, logger):
        """Instantiate driver class
        :ip_address: (str) IP-address of spectrum analyzer, e.g. 'TCPIP0::192.168.50.207::INSTR'
        :logger: (LogClient) Target for logging
        """
        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(ip_address)
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id} at IP {ip_address}.")

        except VisaIOError:
            self.log.error(f"Connection to IP {ip_address} failed.")

    def query(self, command):
        return self.device.query(command)

    def write(self, command):
        return self.device.write(command)

    def query_binary_values(self, command, **kwargs):
        return self.device.query_binary_values(command, **kwargs)

    def write_binary_values(self, command, data, **kwargs):
        return self.device.write_binary_values(command, data, **kwargs)


class Tek70KHelper:
    """ Module with a bunch of helpful functions for the Tektronix70k AWG.
    Mostly just wrappers around sending and receiving text commands. """

    # Markers are uploaded as the 6th and 7th bit in a byte
    MARKER_1_POS = 6
    MARKER_2_POS = 7
    # Markers are sent as bytes with the 6th and/or 7th bit set to 1
    MARKER_0 = (0).to_bytes(length=1, byteorder='little')
    MARKER_1 = (2 ** MARKER_1_POS).to_bytes(length=1, byteorder='little')
    MARKER_2 = (2 ** MARKER_2_POS).to_bytes(length=1, byteorder='little')
    MARKER_12 = (2 ** MARKER_1_POS + 2 ** MARKER_2_POS).to_bytes(length=1, byteorder='little')

    def __init__(self, device):
        """ device can be any object that implements the write(command), query(command) methods
        and the binary and ASCII variants. In particular, it can be a Driver for the Tek70k,
        a Client, or the PyVisa device object itself. """
        self.device = device

    # Using the device to implement these communication functions
    def query(self, command):
        return self.device.query(command)

    def write(self, command):
        return self.device.write(command)

    def query_binary_values(self, command, **kwargs):
        return self.device.query_binary_values(command, **kwargs)

    def write_binary_values(self, command, data, **kwargs):
        return self.device.write_binary_values(command, data, **kwargs)

    def write_file(self, path, string, start_index=0):
        """ Write a string into a target file path on the AWG. Will overwrite any existing data. """
        # Convert string to bytearray, send as binary data, datatype 'B' means signed char sized integers
        # https://docs.python.org/3/library/struct.html#format-characters
        self.write_binary_values(f'MMEMORY:DATA "{path}", {start_index}, ', bytearray(string, encoding='ascii'), datatype='b')

    def read_file(self, path, read_len=None, start_index=0):
        """ Read a string from a target file path on the AWG.  """
        if read_len is None:
            read_len = self.get_file_size(path)

        # Read binary data from the file, interpreting data as actual chars ('c')
        reply = self.query_binary_values(f'MMEMORY:DATA? "{path}", {start_index}, {read_len}', datatype='c')
        # Reply is a list of char bytes, we concatenate them together, then decode as a string
        return b''.join(reply).decode('ascii')

    def get_file_size(self, path):
        """ Get file size of a target file path on the AWG.  """
        return int(self.query(f'MMEMORY:DATA:SIZE? "{path}"'))

    def write_marker(self, wave_name, marker1_arr, marker2_arr=np.array([], dtype=int), start_index=0):
        """ Takes two arrays for the 2 markers and writes them into the marker for a waveform.
        wave_name (str):
            Name of waveform to write marker data into
        marker1_arr, marker2_arr (list):
            Marker data to be written, specified in a list/array consisting of only 0 or 1
        start_index (int):
            Location in the waveform to start writing the marker data from
        """

        # Pad the arrays with 0 to have the same length
        max_len = max(len(marker1_arr), len(marker2_arr))
        marker1_arr = np.pad(marker1_arr, (0, max_len - len(marker1_arr)))
        marker2_arr = np.pad(marker2_arr, (0, max_len - len(marker2_arr)))

        # Ensure all values are 0 or 1
        if not ((np.all((marker1_arr == 0) | (marker1_arr == 1))) and
                (np.all((marker2_arr == 0) | (marker2_arr == 1)))):
            raise ValueError("All marker values must be 0 or 1.")

        # Construct bytes by shifting the bits to their respective bit positions
        # Then convert each sample into 1 byte (uint8)
        marker_int_arr = (marker1_arr << self.MARKER_1_POS) + (marker2_arr << self.MARKER_2_POS)
        marker_bytes_arr = [int(i).to_bytes(length=1, byteorder='little') for i in marker_int_arr]

        # 'c' means datatype char
        # https://docs.python.org/3/library/struct.html#format-characters
        self.write_binary_values(f'WLIST:WAV:MARKER:DATA "{wave_name}", '
                                 f'{start_index},', marker_bytes_arr, datatype='c')

    def read_marker(self, wave_name, read_len, start_index=0):
        """ Returns two arrays for the 2 markers in a waveform.
        wave_name (str):
            Name of waveform to read marker data from
        read_len (int):
            Number of marker datapoints to read
        start_index (int):
            Location in the waveform to start read the marker data from
        returns: (marker1_arr, marker_2), lists of ints value 0 or 1.
        """
        # Get an array of bytes from device, datatype converts them into uint8
        int_arr = self.query_binary_values(
            f'WLIST:WAV:MARKER:DATA? "{wave_name}", '
            f'{start_index}, {read_len}', datatype='B', container=np.array)

        # To extract individual bits, right shift to the appropriate position and mask last digit
        return ((int_arr >> self.MARKER_1_POS) & 1,
                (int_arr >> self.MARKER_2_POS) & 1)

    def change_dir(self, drive, path):
        self.write(f'MMEM:MSIS "{drive}:"')
        self.write(f'MMEM:CDIR "{path}"')

    def get_dir(self):
        return self.query('MMEM:CDIR?')

    def reset(self):
        self.write('*RST')

    def wait(self):
        self.write('*WAI')

    def set_output_state(self, state, ch=1):
        """ Set output state of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :state: (int) 0 or 1 turns off (on) the channel
        """
        self.write(f'OUTPUT{ch}:STATE {state}')

    def get_output_state(self, ch=1):
        """ Get output state of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :returns: (int) Current output state specified as 0 or 1
        """
        state = int(self.query(f'OUTPUT{ch}:STATE?'))
        return state

    def set_run_mode(self, mode, ch=1):
        """ Set run mode of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :mode: (str) Mode from the set ["CONT", "TRIG", "TCON"]
        """
        self.write(f'SOURCE{ch}:RMODE {mode}')

    def get_run_mode(self, ch=1):
        """ Get run mode of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :returns: (str) Mode from the set ["CONT", "TRIG", "TCON"]
        """
        mode = self.query(f'SOURCE{ch}:RMODE?')
        return mode

    def get_awg_state(self):
        """ Get run state of the AWG.
        :returns: (int) 0: Stopped, 1: Waiting for trig, 2: Running
        """
        mode = int(self.query('AWGCONTROL:RSTATE?'))
        return mode

    def awg_run(self):
        """ Starts the AWG waveform/sequence running.
        Fails if waveforms or sequences are not assigned.
        """
        self.write('AWGCONTROL:RUN')

    def awg_stop(self):
        """ Stops the AWG waveform/sequence from runing. """
        self.write('AWGCONTROL:STOP')

    def change_plugin(self, plugin):
        if plugin not in ["Equation Editor", "Basic Waveform"]:
            raise ValueError(f"Invalid plugin {plugin}.")
        self.write(f'WPLUGIN:ACTIVE "{plugin}"')
        self.wait()

    def assign_sequence(self, seq_name, track=1, ch=1):
        """ Assign a specified track of sequence to a specified channel """
        self.write(f'SOURCE{ch}:CASSET:SEQ "{seq_name}", {track}')

    def assign_waveform(self, wave_name, ch=1):
        """ Assign a waveform a specified channel """
        self.write(f'SOURCE{ch}:CASSET:WAV "{wave_name}"')

    def clear_all_waveforms(self):
        self.write('WLIST:WAV:DEL ALL')

    def clear_all_sequences(self):
        self.write('SLIST:SEQ:DEL ALL')

    def create_new_sequence(self, name):
        """ Create new sequence with 0 steps """
        self.write(f'SLIST:SEQ:NEW "{name}", 0')
        return Sequence(name)

    def compile_equation(self, path):
        """ Compile equation file and import waveforms defined in trhe file. """
        # Make sure we are in editor mode
        self.write('WPLUGIN:ACTIVE "Equation Editor"')
        self.wait()
        self.write(f'AWGCONTROL:COMP "{path}"')


class Sequence:
    """ Represents a Sequence on the Tektronix70k Sequencer Editor.
    name (str):
        name of the sequence
    step_ptr (int):
        Index of the first EMPTY step (i.e. will be 1 for an empty seq)
    wave_table (dict [str: int]):
        Associates a given waveform or subsequence name with
        the step number in the sequence
    """

    def __init__(self, name, step_ptr=1):
        self.name = name
        self.step_ptr = step_ptr
        self.wave_table = {}

    def __repr__(self):
        return f"Sequence({self.name}, step_ptr = {self.step_ptr}, wave_table = {self.wave_table})"
