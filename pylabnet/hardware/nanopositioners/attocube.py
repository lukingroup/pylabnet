""" Module for controlling attocube open-loop nanopositioners using the ANC300 controller

NOTE: Substantial part of this driver has been adapted from the very nice pymeasure project:
https://pymeasure.readthedocs.io/en/latest/api/instruments/attocube/anc300.html
"""


from pylabnet.network.core.service_base import ServiceBase
from pylabnet.utils.logging.logger import LogHandler
from telnetlib import Telnet
import time
import re


# Room temperature limits as cautions default limit.
DEFAULT_LIMITS = {
    "freq_lim": 10000,
    "step_voltage_lim": 60
}


# Decorator used to check if provided channel is valid.
def check_channel(f):
    def wrapper(*args, **kw):

        class_instance = args[0]

        # Retrieve Channel number.
        if 'channel' in kw.keys():
            channel = kw['channel']
        else:
            channel = args[1]
        if class_instance.channel_valid(channel):
            return f(*args, **kw)
        else:
            pass
    return wrapper


class ANC300:

    # compiled regular expression for finding numerical values in reply strings
    _reg_value = re.compile(r"\w+\s+=\s+(\w+)")

    def __init__(self, host, port=0, query_delay=0.001, passwd=None, limits=DEFAULT_LIMITS, logger=None):
        """ Instantiate ANC300 objcet.
        :param host: IP of telnet connection.
        :param port: Port of telnet connection.
        :param query_delay: Delay between queries (ins s).
        :param passwd: Telnet login password.
        :param limits: Voltage limit dictionary.
        :param logger: Log client.
        """

        self.log = LogHandler(logger)
        self.query_delay = query_delay
        self.lastcommand = ""
        self.freq_lim = limits["freq_lim"]
        self.step_voltage_lim = limits["step_voltage_lim"]

        # Instantiate Telnet Connection
        self.connection = Telnet(host, port)

        # Setup terminations
        self.read_termination = '\r\n'
        self.write_termination = self.read_termination

        # Log into telnet client
        time.sleep(query_delay)
        ret = self._read(check_ack=False)
        self._write(passwd, check_ack=False)
        time.sleep(self.query_delay)
        ret = self._read(check_ack=False)
        authmsg = ret.split(self.read_termination)[1]

        if authmsg != 'Authorization success':
            self.log.error(f"Attocube authorization failed '{authmsg}'")
        else:

            # Read board serial number
            board_ver = self._write("getcser")

            # Check how many exes are available
            valid_axes, num_axes = self._check_num_channels()
            self.axes = valid_axes
            self.num_axes = num_axes

            self.log.info(f"Connected to {board_ver} with {self.num_axes} available axes.")

    def _check_num_channels(self):
        """ Checks how many axes are available

        :returns: valid_axis, list containing the axis indices (1-indexed), num_axis, integer
        """

        valid_axis = []
        for i in range(1, 8):
            axis_serial = self._write(f"getser {i}", check_axes=True)
            if axis_serial != 'Wrong axis type':
                valid_axis.append(i)

        num_axis = len(valid_axis)
        return valid_axis, num_axis

    def channel_valid(self, channel):
        """ Checks if channel number matches total number of detected channels.

        :returns: channel_valid, boolean. If true, the channel is valid.
        """

        channel_valid = False
        if channel not in self.axes:
            self.log.error(f"Channel {channel} not valid, available channels are {self.axes}.")
        else:
            channel_valid = True
        return channel_valid

    def _check_acknowledgement(self, reply, msg=""):
        """ checks the last reply of the instrument to be 'OK', a log error is raised

        :param reply: last reply string of the instrument
        :param msg: optional message for the eventual error
        """
        if reply != 'OK':
            if msg == "":  # clear buffer
                msg = reply
                self._read()
            self.log.error("AttocubeConsoleAdapter: Error after command "
                           f"{self.lastcommand} with message {msg}")

    def _read(self, check_ack=True, check_axes=False):
        """ Reads a reply of the instrument which consists of two or more
        lines. The first ones are the reply to the command while the last one
        is 'OK' or 'ERROR' to indicate any problem. In case the reply is not OK
        a ValueError is raised.
        :param check_axes: Supressed error message (only for check axis command).
        :returns: Cleaned up response of the instruments (stripped by the status indicator
        and initial command).
        """
        time.sleep(self.query_delay)
        ret = self.connection.read_some().decode() + \
            self.connection.read_very_eager().decode()

        raw = ret.strip(self.read_termination)

        if check_ack:
            check = ""
            split_return = raw.rsplit(sep='\n')
            if len(split_return) == 3:
                # No argument returned
                check = split_return[-2].strip("\r")
                ret = split_return[0].strip("\r")
            elif len(split_return) == 4:
                check = split_return[-2].strip("\r")
                ret = split_return[1].strip("\r")

            if not check_axes:
                self._check_acknowledgement(check, ret)

        return ret

    def _extract_value(self, reply):
        """ preprocess_reply function for the Attocube console. This function
        tries to extract <value> from 'name = <value> [unit]'. If <value> can
        not be identified the original string is returned.
        :param reply: reply string
        :returns: float with only the numerical value, or the original string
        """
        r = self._reg_value.search(reply)
        if r:
            return r.groups()[0]
        else:
            return reply

    def _write(self, command, check_ack=True, check_axes=False):
        """ Writes a command to the instrument
        :param command: command string to be sent to the instrument
        :param check_ack: boolean flag to decide if the acknowledgement is read
            back from the instrument. This should be True for set pure commands
            and False otherwise.
        :param check_axes: Supressed error message (only for check axis command).
        :return: Returns cleaned up intrument response if check_ack is chosen,
        'None' otherwise.
        """
        time.sleep(self.query_delay)
        self.lastcommand = command
        command = command + self.write_termination
        self.connection.write(command.encode())

        if check_ack:
            reply = self._read(check_ack=check_ack, check_axes=check_axes)
        else:
            reply = None
        return reply

    @check_channel
    def _set_mode(self, channel, mode):
        """ Set mode of controller
        :param channel: (int) index of channel from 1 to self.num_ch

        :param mode: String indicating mode, which can be gnd (grounded), cap,
        (capacitance measurement), and stp (Step mode)
        """
        self._write(f"setm {str(channel)} {str(mode)}")

    @check_channel
    def ground(self, channel):
        """ Grounds channel

        :param channel: (int) index of channel from 1 to self.num_ch
        """
        self._set_mode(channel, 'gnd')
        self.log.info(f"Grounded channel {channel}.")

    @check_channel
    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None):
        """ Sets parameters for motion

        Leave parameter as None in order to leave un-changed

        :param channel: (int) index of channel from 1 to self.num_ch
        :param mode: (str) default is 'step',
        :param freq: (int) frequency in Hz from 1 to 20000
        :param amp: (float) amplitude in volts from 0 to 100
        """

    @check_channel
    def get_step_voltage(self, channel):
        """ Returns the step voltage in V

        :param channel: (int) channel index (from 1)
        """
        return self._extract_value(self._write(f"getv {str(channel)}"))

    @check_channel
    def set_step_voltage(self, channel, voltage=30):
        """ Sets the step voltage to the piezo

        :param channel: (int) channel index from 1 to self.num_ch
        :param voltage: (float) voltage to set from 0 to 150 V (default is 30)
        """

        if not (0 <= voltage <= self.step_voltage_lim):
            self.log.error(f"Step voltage has to be between 0 V and {self.step_voltage_lim} V.")
            return

        self._write(f"setv {str(channel)} {str(voltage)}")
        self.log.info(f"Change step voltage of channel {channel} to {voltage} V.")

    @check_channel
    def get_step_frequency(self, channel):
        """ Returns the step frequency on channel

        :param channel: (int) channel index from 1 to self.num_ch
        """

        return self._extract_value(self._write(f"getf {str(channel)}"))

    @check_channel
    def set_step_frequency(self, channel, freq=1000):
        """ Sets the step voltage to the piezo

        :param channel: (int) channel index from 1 to self.num_ch
        :param voltage: (float) voltage to set from 0 to 10000 Hz (default is 1000 Hz)
        """

        if not (0 <= freq <= self.freq_lim):
            self.log.error(f"Frequency has to be between 0 Hz and {self.freq_lim} Hz")
            return

        self._write(f"setf {str(channel)} {str(freq)}")
        self.log.info(f"Change step frequency of channel {channel} to {freq} Hz.")

    @check_channel
    def n_steps(self, channel, n=1):
        """ Takes n steps

        :param channel: (int) channel index from 1 to self.num_ch
        :param n: (int) number of steps to take, negative is in opposite direction
        """

        # Set into stepping mode
        self._set_mode(channel, 'stp')

        if n > 0:
            self._write(f"stepu {str(channel)} {str(n)}", check_ack=False)
        else:
            self._write(f"stepd {str(channel)} {str(abs(n))}", check_ack=False)

        self.log.info(f"Took {n} steps on channel {channel}.")

    @check_channel
    def get_capacitance(self, channel):
        """ Measures capacitance of positioner

        :param channel: (int) channel index from 1 to self.num_ch
        :return: Returns C in nF
        """

        # Set into stepping mode
        self._set_mode(channel, 'cap')
        time.sleep(1)
        cap = float(self._extract_value(self._write(f"getc {str(channel)}")))
        self.log.info(f"Capacitance measured on chanel {channel}: {cap} nF.")
        return cap

    @check_channel
    def get_output_voltage(self, channel):
        """ Get output voltage

        :param channel: (int) channel index from 1 to self.num_ch
        :return: Returns step voltage in volt
        """
        return float(self._extract_value(self._write(f"geto {str(channel)}")))

    @check_channel
    def move(self, channel, backward=False):
        """ Moves continously

        :param channel: (int) channel index from 1 to self.num_ch
        :param backward: (bool) whether or not to step in backwards direction (default False)
        """
        # Set into stepping mode
        self._set_mode(channel, 'stp')

        if not backward:
            self._write(f"stepu {str(channel)} c", check_ack=False)
        else:
            self._write(f"stepd {str(channel)} c", check_ack=False)

    @check_channel
    def stop(self, channel):
        """ Terminates any ongoing movement

        :param channel: (int) channel index from 1 to self.num_ch
        """
        self._write(f"stop {str(channel)}")
        self.log.info(f"Stopped channel {channel}.")

    @check_channel
    def is_moving(self, channel):
        """ Returns whether or not the positioner is moving

        :param channel: (int) channel index from 1 to self.num_ch

        :return: (bool) true if moving
        """
        output_voltage = self.get_output_voltage(channel)

        if output_voltage < 1E-3:
            return False
        else:
            return True

    def stop_all(self):
        """ Terminates any ongoing movement on all axes"""

        for i in self.axes:
            self.stop(i)

    def ground_all(self):
        """ Grounds all positioners"""

        for i in self.axes:
            self.ground(i)
