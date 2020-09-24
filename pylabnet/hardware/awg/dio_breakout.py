""" Module for controlling homebuilt breakout box for HDAWG DIO"""

from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import value_to_bitval, bitval_to_value


class Driver:

    BOARDS = 8

    def __init__(self, address=None, logger=None):
        """Instantiate driver class.

        :address: Address of the device, e.g. 'ASRL3::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: An instance of a LogClient.
        """

        # Instantiate log
        self.log = LogHandler(logger=logger)
        self.addr = address

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(self.addr)
            self.log.info(f"Successfully connected to {self.device}.")

            # Configure device grammar
            self.device.write_termination = ';'
        except VisaIOError:
            self.log.error(f"Connection to {self.addr} failed.")
            raise

    def measure_voltage(self, board, channel):
        """ Measures the current voltage on a particular channel of a particular board

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3

        :return: (float) voltage in volts (into open-loop)
        """

        # Only proceed if we can correctly set the current board and channel
        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not measure the voltage for board {board} channel {channel}')
            return float(-777)

        return bitval_to_value(
            int(self.device.query('v').split()[-1]),
            bits=12,
            min=0,
            max=10
        )

    def set_high_voltage(self, board, channel, voltage):
        """ Sets a channel's high voltage

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3
        :param voltage: (float) voltage in V between 0 and 10 (into open-loop)

        :return: (int) 0 if successful
        """

        # Only proceed if we can correctly set the current board and channel
        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not measure the voltage for board {board} channel {channel}')
            return float(-777)

        return self._set_high_voltage(voltage)

    def set_low_voltage(self, board, channel, voltage):
        """ Sets a channel's low voltage

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3
        :param voltage: (float) voltage in V between 0 and 10 (into open-loop)

        :return: (int) 0 if successful
        """

        # Only proceed if we can correctly set the current board and channel
        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not measure the voltage for board {board} channel {channel}')
            return float(-777)

        return self._set_low_voltage(voltage)
    
    def get_high_voltage(self, board, channel):
        """ Gets a channel's high voltage

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3

        :return: (float) voltage in V from 0 to 10
        """

        # Only proceed if we can correctly set the current board and channel
        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not measure the voltage for board {board} channel {channel}')
            return float(-777)

        return bitval_to_value(
            int(self.device.query('h').split()[-1]),
            bits=16,
            min=0,
            max=10
        )

    def get_low_voltage(self, board, channel):
        """ Gets a channel's low voltage

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3

        :return: (float) voltage in V from 0 to 10
        """

        # Only proceed if we can correctly set the current board and channel
        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not measure the voltage for board {board} channel {channel}')
            return float(-777)

        return bitval_to_value(
            int(self.device.query('l').split()[-1]),
            bits=16,
            min=0,
            max=10
        )
    
    def save(self):
        """ Saves current state of low/high for all channels to non-volatile memory
        
        :return: (int) 0 if successful
        """

        # This fails randomly due to nondeterministic response, which we need to handle
        read = 0
        while read < 10:
            self.device.write('S')
            try:
                self.device.read()
                read = 11
            except VisaIOError:
                read += 1
            except UnicodeDecodeError:
                read += 1
        if read > 10:
            self.log.info('Saved current DIO breakout settings successfully')
            return 0
        else:
            self.log.warn('Failed to save DIO breakout settings.'
                          'Connection may be corrupted.')
            return 1
    
    def override(self, board, channel, state=True):
        """ Overrides HDAWG output

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3
        :param state: (bool) whether or not to force hi or lo

        :return: (int) 0 if successful
        """

        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not override board {board} channel {channel}')
            return float(-777)

        self.device.write(f'F {1 if state else 0}')
        if int(self.device.query('b').rstrip()[-1]) != board:
            self.log.warn(f'Error in overriding board {board} channel {channel}')
            return float(-1)

        self.log.info(f'Board {board} channel {channel} in override mode')
        return 0
    
    def disable_override(self, board, channel):
        """ Disables the override

        :param board: (int) integer between 0 and 7 (assuming 8 boards)
        :param channel: (int) integer between 0 and 3

        :return: (int) 0 if successful
        """

        if self._set_board(board) + self._set_channel(channel):
            self.log.warn(f'Did not disable override for board {board} channel {channel}')
            return float(-777)

        self.device.write('F -1')
        if int(self.device.query('b').rstrip()[-1]) != board:
            self.log.warn(f'Error in disabling override for board {board} channel {channel}')
            return float(-1)

        self.log.info(f'Board {board} channel {channel} override has been disabled')
        return 0
    
    def close(self):
        """ Closes the connection to the device """

        self.device.close()
        self.log.info(f'Closed connection to device at {self.addr}')
    
    # Technical methods (not to be exposed)

    def _set_board(self, board):
        """ Sets the current board (to update)

        :param board: (int) integer between 0 and 7 (assuming 8 boards)

        :return: (int) 0 if successful
        """

        board = int(board)
        # Check within bounds
        if board < 0 or board > self.BOARDS-1:
            self.log.warn(f'Board to set must be an integer between 0 and {self.BOARDS-1}')
            return 1

        self.device.write(f'B {board}')

        # Check successful write (and clear the buffer)
        if int(self.device.query('b').rstrip()[-1]) != board:
            self.log.warn(f'Failed to set current board to {board}')
            return 2

        return 0

    def _set_channel(self, channel):
        """ Sets the current channel (to update)

        :param channel: (int) integer between 0 and 3

        :return: (int) 0 if successful
        """

        channel = int(channel)
        # Check within bounds
        if channel < 0 or channel > 3:
            self.log.warn(f'Channel to set must be an integer between 0 and 3')
            return 1

        self.device.write(f'C {channel}')

        # Check successful write (and clear the buffer)
        if int(self.device.query('c').rstrip()[-1]) != channel:
            self.log.warn(f'Failed to set current channel to {channel}')
            return 2

        return 0

    def _set_high_voltage(self, voltage):
        """ Sets the current channel's high voltage

        :param voltage: (float) voltage in V between 0 and 10 (into open-loop)

        :return: (int) 0 if successful
        """

        voltage = float(voltage)
        # Check within bounds
        if voltage < 0 or voltage > 10:
            self.log.warn(f'Can only set voltage between 0 and 10 V')
            return 1

        bitval = value_to_bitval(voltage, bits=16, min=0, max=10)
        self.device.write(f'H {bitval}')

        # Check successful write (and clear the buffer)
        if int(self.device.query('h').split()[-1]) != bitval:
            self.log.warn(f'Failed to set high voltage to {voltage} V')
            return 2

        return 0

    def _set_low_voltage(self, voltage):
        """ Sets the current channel's low voltage

        :param voltage: (float) voltage in V between 0 and 10 (into open-loop)

        :return: (int) 0 if successful
        """

        voltage = float(voltage)
        # Check within bounds
        if voltage < 0 or voltage > 10:
            self.log.warn(f'Can only set voltage between 0 and 10 V')
            return 1

        bitval = value_to_bitval(voltage, bits=16, min=0, max=10)
        self.device.write(f'L {bitval}')

        # Check successful write (and clear the buffer)
        if int(self.device.query('l').split()[-1]) != bitval:
            self.log.warn(f'Failed to set low voltage to {voltage} V')
            return 2

        return 0
