from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler
import numpy as np


class Driver():
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

    def reset(self):
        """ Perform factory reset. """

        self.device.write('*RST')
        self.log.info("Reset to factory settings successful.")

    def set_output_state(self, ch, state):
        """ Set output state of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :state: (int) 0 or 1 turns off (on) the channel
        """

        self.device.write(f'OUTPUT{ch}:STATE {state}')
        self.log.info(f"Output of channel {ch} set to state {state}")

    def get_output_state(self, ch):
        """ Get output state of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :returns: (int) Current output state specified as 0 or 1
        """

        state = int(self.device.query(f'OUTPUT{ch}:STATE?'))
        self.log.info(f"Output of channel {ch} is current in state {state}")
        return state

    def set_run_mode(self, ch, mode):
        """ Set run mode of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :mode: (str) Mode from the set ["CONT", "TRIG", "TCON"]
        """

        self.device.write(f'SOURCE{ch}:RMODE {mode}')
        self.log.info(f"Mode of channel {ch} set to mode {mode}")

    def get_run_mode(self, ch):
        """ Get run mode of a specified channel.
        :ch: (int) Channel specified, 1-indexed
        :returns: (str) Mode from the set ["CONT", "TRIG", "TCON"]
        """

        mode = self.device.query(f'SOURCE{ch}:RMODE?')
        self.log.info(f"Channel {ch} is currently in mode {mode}")
        return mode

    def run(self):
        """ Starts the AWG waveform/sequence running.
        Fails if waveforms or sequences are not assigned. """

        self.device.write('AWGCONTROL:RUN')
        self.log.info("Attemped to start AWG.")

        # Check if still stopped, e.g. if waveforms not assigned
        if self.get_output_state() == 0:
            self.log.error("AWG has failed to start!")

    def stop(self):
        """ Stops the AWG waveform/sequence from runing. """

        self.device.write('AWGCONTROL:STOP')
        self.log.info("AWG is stopped.")

    def get_output_state(self):
        """ Get AWG running state.
        :returns: (str) Current running state of AWG.
        """

        # Trig means waiting for trigger
        state_dict = {0: "STOP", 1: "TRIG", 2: "RUN"}
        state = int(self.device.query('AWGCONTROL:RSTATE?'))
        self.log.info(f"AWG state is {state_dict[state]}")
        return state_dict[state]
