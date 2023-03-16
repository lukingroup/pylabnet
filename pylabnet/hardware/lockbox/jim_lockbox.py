import serial
import re
import serial.tools.list_ports
import numpy as np

from serial import SerialException
from pylabnet.utils.logging.logger import LogHandler


class Driver:

    END_SEP = ";"
    VALID_FIELDS = ["dCount1", "Count2", "Timebase", "PVal", "IVal", "DVal", "ErrorVal", "Integrator", "Offset", "PIDOut"]

    def __init__(self, com_port, baudrate, timeout, logger=None):
        """Instantiate serial connection.

        :com_address: COM address of the lockbox, e.g. 'COM4'
            Can be read out by using
                ports = serial.tools.list_ports.comports()
                for port, desc, hwid in ports:
                        print(f"{port}: {desc} [{hwid}]")
            E.g. "COM4: USB Serial Port (COM4) [USB VID:PID=0403:6015 SER=DN01BJKRA]"

        :logger: An instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)
        self.ports = serial.tools.list_ports.comports()
        self.com_port = com_port
        self.baudrate = baudrate
        self.timeout = timeout

        # Desired com_port not in the list of connected devices
        if com_port not in [p[0] for p in self.ports]:
            err_msg = f"Com port {com_port} not found."
            self.log.error(err_msg)
            raise ConnectionError(err_msg)

        # Acquire information about the desired com_port
        for port, desc, hwid in self.ports:
            if com_port == port:
                self.log.info(f"Found port {port}: {desc} - ID [{hwid}].")
                break

        # Try and open a connection to it
        try:
            self.device = serial.Serial(com_port, baudrate=baudrate, timeout=timeout)
            self.log.info(f"Successfully connected to {port}: {desc} - ID [{hwid}].")
        except SerialException:
            self.log.error(f"Connection to {com_port} failed.")

    # Destructor, called when object is deleted
    def __del__(self):
        self.device.close()

    def search_field(self, string, field):
        """ Searches for a field of the format [FIELD] = xxxxxx
        where the xxx are float numbers, and returns the extract numbers.

        :param msg: (str) message to be sent
        """

        if field not in self.VALID_FIELDS:
            self.log.error(f"Invalid Lockbox field {field}.")
            return 0

        regex_search = re.search(f"{field} = ([0-9\.]*)", string)

        try:
            return float(regex_search.group(1))
        # ValueError if float conversion failed, AttributeError if regex had no results (None)
        except (ValueError, AttributeError) as e:
            self.log.error(e)
            return 0

    def send_command(self, msg):
        """ Sends a message to the device.

        :param msg: (str) message to be sent
        """
        self.device.write((msg + self.END_SEP).encode('utf-8'))

    def read_reply(self, length=200):
        """ Reads a message from the device.

        :param length: (int) max length in bytes to be read, or until timeout is reached.
        :return: (str) reply from the device
        """
        return self.device.read(length).decode('utf-8')

    def send_read(self, msg, length=200):
        """ Sends a message to the device and reads its reply.

        :param msg: (str) message to be sent
        :param length: (int) max length in bytes to be read, or until timeout is reached.
        :return: (str) reply from the device
        """
        self.send_command(msg)
        return self.read_reply(length)

    def send_read_verify(self, msg, length=200):
        """ Sends a message to the device, reads its reply, and verify that it has accepted the command.
        The expected response for a command that sets variables is as follows:
            E.g. Send "IS 1.0;"  , expect reply "IS 1.0!" for accepted command.
            Semicolon is replaced with exclamation mark.

        :param msg: (str) message to be sent
        :param length: (int) max length in bytes to be read, or until timeout is reached.
        :return: (str) reply from the device
        """

        reply = self.send_read(msg, length)
        if reply != msg + "!":
            self.log.error(f"Unexpected reply '{reply}' from Lockbox.")
        return reply

    def set_P(self, P):
        """ Sets the proportional term in PID.
        :param P: (float) Proportional coefficient
        """
        msg = f"PS {P}"
        return self.send_read_verify(msg)

    def set_I(self, I):
        """ Sets the integral term in PID.
        :param I: (float) Integral coefficient
        """
        msg = f"IS {I}"
        return self.send_read_verify(msg)

    def set_D(self, D):
        """ Sets the differential term in PID.
        :param D: (float) Differential coefficient
        """
        msg = f"DS {D}"
        return self.send_read_verify(msg)

    def set_int_time(self, t):
        """ Sets the integration time for the PID. Should be set to be
        long enough for good SNR while not overflowing the count buffer (65535 counts)
        :param t: (float) Integration time in us
        """
        msg = f"TS {t}"
        return self.send_read_verify(msg)

    def set_offset(self, offset):
        """ Sets the PID output offset.
        :param offset: (float) PID output offset, should be between 0 to 65535.
        """
        msg = f"OS {offset}"
        return self.send_read_verify(msg)

    def get_status(self):
        """ Get the status of the PID system.
        :return: (str) System status output
        """
        msg = "d"
        return self.send_read(msg)

    def get_all_vals(self):
        """ Get all the numerical values from the status dump.
        :return: (list) List of parameters describing the PID system
        [dCount1, Count2, Timebase, PVal, IVal, DVal, ErrorVal, Integrator, Offset, PIDOut]
        """
        status = self.get_status()
        status_lines = status.split("\r\n")[:-1] # Last line is just "!"
        return [float(line.split(" = ")[1]) for line in status_lines]

    def get_P(self):
        """ Get the current value of the proportional term.
        :return: (float) Proportional coefficient
        """
        s = self.get_status()
        return self.search_field(s, "PVal")

    def get_I(self):
        """ Get the current value of the integral term.
        :return: (float) Integral coefficient
        """
        s = self.get_status()
        return self.search_field(s, "IVal")

    def get_D(self):
        """ Get the current value of the differential term.
        :return: (float) Differential coefficient
        """
        s = self.get_status()
        return self.search_field(s, "DVal")

    def get_int_time(self):
        """ Get the current value of the integration time.
        :return: (float) Integration time in us
        """
        s = self.get_status()
        return self.search_field(s, "Timebase")

    def get_offset(self):
        """ Get the current value of the PID output offset.
        :return: (float) PID output offset
        """
        s = self.get_status()
        return self.search_field(s, "Offset")

    def get_errorval(self):
        """ Get the current PID error value (difference between the 2 count channels)
        :return: (float) PID error value
        """
        s = self.get_status()
        return self.search_field(s, "ErrorVal")

    def get_integrator(self):
        """ Get the current PID integrator value
        :return: (float) PID integrator value
        """
        s = self.get_status()
        return self.search_field(s, "Integrator")

    def get_PID_output(self):
        """ Get the current PID output value. Limits are 0 - 65535, corresponding to 0 - 10V output.
        :return: (float) PID output value
        """
        s = self.get_status()
        return self.search_field(s, "PIDOut")

    def reset(self):
        """ Resets the integrator by getting current I value, and setting it again.
        Changing P, I, D or offset will reset the integrator, so the choice of "I" is arbitrary.
        """

        curr_IVal = self.get_I()
        self.set_I(curr_IVal)
