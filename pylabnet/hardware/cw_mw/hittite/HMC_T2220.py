from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver():

    def reset(self):
        """ Create factory reset"""
        self.device.write('*RST')
        self.log.info("Reset to factory settings successfull.")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class.

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            self.device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {self.device_id}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

        # Reset to factory settings.
        self.reset()

        # Read and store min and max power
        self.power_min, self.power_max = [
            float(
                self.device.query(f'pow? {string}')
            )
            for string in ['min', 'max']
        ]

        # Read and store min and max frequency
        self.freq_min, self.freq_max = [
            float(
                self.device.query(f'freq? {string}')
            )
            for string in ['min', 'max']
        ]
    
    def output_on(self):
        """ Turn output on."""

        self.device.write('OUTPut ON')

        if self.check_power_out_of_range():
            self.log.warn(
            f"Choosen power level of {self.get_power()} lies outside of calibration range."
        )

        self.log.info(f"Output of {self.device_id} turned on.")

    def output_off(self):
        """ Turn output off."""

        self.device.write('OUTP OFF')
        self.log.info(f"Output of {self.device_id} turned off.")

    def check_power_out_of_range(self):
        """ Returns true if current power is outside of calibration range, False otherwise"""

        if not self.is_output_on():
            self.log.warn("Please enable output on to check if calibration out of range")
            return

        # Query status register and do bitwise AND to check status of bit 3
        if int(self.device.query('Status:Questionable:Condition?')) & 8:
            power_out_of_range = True
        else:
            power_out_of_range = False

        return power_out_of_range

    def is_output_on(self):
        """Returns True1 if output is enabled, False otherwise)"""
        return bool(int(self.device.query('OUTPut?')))

    def set_freq(self, freq):
        """ Set frequency (in Hz)

        :freq: Target frequency in Hz
        """
        if not self.freq_min <= freq <= self.freq_max:
            self.log.error(f"Frequency must be between {self.freq_min} Hz and {self.freq_max} Hz")
        self.device.write(f'freq {freq}')
        self.log.info(f"Frequency of {self.device_id} set to {freq} Hz.")

    def get_freq(self):
        """Returns current frequency setting"""
        return float(self.device.query('freq?'))

    def set_power(self, power):
        """ Set output power (in dBm) 

        :power: Target power in dBm
        """

        if not self.power_min <= power <= self.power_max:
            self.log.error(f"Power must be between {self.power_min} dBm and {self.power_max} dBm")

        self.device.write(f'pow {power}')
        self.log.info(f"Output power of {self.device_id} set to {power} dBm.")

        # If output enabled, check if power is outside of calibration range.
        if self.is_output_on():
            if self.check_power_out_of_range():
                    self.log.warn(
                        f"Choosen power level of {self.get_power()} lies outside of calibration range."
                    )

    def get_power(self):
        """Returns current output power setting"""
        return float(self.device.query('pow?'))