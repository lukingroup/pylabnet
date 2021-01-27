from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver():
    POWER_RANGE = [-120, 30]    # acceptable power range in dBm
    POWER_PRECISION = 2 # number of digits of precision for power
    FREQ_RANGE = [1e7, 2e10]    # acceptable frequency range in Hz

    def __init__(self, gpib_address, logger):
        """ Instantiate driver class, connects to device

        :param gpib_address: GPIB-address of the device,
            can be found with pyvisa.ResourceManager.list_resources()
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            self.device.read_termination = '\n'
            self.device_id = self.device.query('*IDN?')
            self.log.info(f'Successfully connected to {self.device_id}')
        except VisaIOError:
            self.log.error(f'Connection to {gpib_address} failed')
            raise

    def set_power(self, power):
        """ Sets power of MW source

        :param power: (float) output power to set in dBm
        """

        power = round(power, self.POWER_PRECISION)

        # Check for valid range
        if power < self.POWER_RANGE[0] or power > self.POWER_RANGE[1]:
            self.log.warn(
                f'Warning, power outside acceptable range {self.POWER_RANGE}. '
                f'Output power was not updated.'
            )
        # Set power
        else:
            self.device.write(f'POW {power}')
            self.log.info(f'Set MW power to {power}')

    def set_freq(self, freq):
        """ Sets power of MW source

        :param freq: (float) output frequency in Hz
        """

        freq = int(round(freq))

        # Check for valid range
        if freq < self.FREQ_RANGE[0] or freq > self.FREQ_RANGE[1]:
            self.log.warn(
                f'Warning, frequency outside acceptable range {self.FREQ_RANGE}. '
                f'Output frequency was not updated.'
            )
        # Set freq
        else:
            self.device.write(f'FREQ {freq}')
            self.log.info(f'Set MW freq to {freq}')

    def output_on(self):
        """ Turn output on """

        self.device.write('OUTP ON')
        self.log.info('MW output turned on')

    def output_off(self):
        """ Turn output off """

        self.device.write('OUTP OFF')
        self.log.info('MW output turned off')
