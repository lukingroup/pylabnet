""" Module for controlling homebuilt breakout box for HDAWG DIO"""

from pyvisa import VisaIOError, ResourceManager


class Driver:

    def __init__(self, gpib_address=None, logger=None):
        """Instantiate driver class.

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: An instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            self.log.info(f"Successfully connected to {self.device}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

    def _set_board(self, board):
        """ Sets the current board (to update)

        :param board: (int) integer between 0 and 7
        """

        board = int(board)
        if board < 0 or board > 7:
            self.log.warn('Board to set must be an integer between 0 and 7')
        else:
            reply = self.device.query(f'B{board};')
