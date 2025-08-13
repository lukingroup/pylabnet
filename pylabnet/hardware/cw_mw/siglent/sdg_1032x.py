from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver():

    def __init__(self, device_id, logger):
        """Instantiate driver class.

        :device_id: USB address of the device
        :logger: An instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()

        try:
            self.device_id = device_id
            self.device = self.rm.open_resource(device_id)
            device_name = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {self.device_id}.")
            self.log.info(f"Device returned {device_name}.")
        except VisaIOError:
            self.log.error(f"Connection to {device_id} failed.")

    def output_on(self, ch):
        """ Turn output on."""
        self.device.write(f"C{ch}:OUTPUT ON")
        self.log.info(f"Output Channel {ch} of {self.device_id} turned on.")

    def output_off(self, ch):
        """ Turn output off."""
        self.device.write(f"C{ch}:OUTPUT OFF")
        self.log.info(f"Output Channel {ch} of {self.device_id} turned off.")
