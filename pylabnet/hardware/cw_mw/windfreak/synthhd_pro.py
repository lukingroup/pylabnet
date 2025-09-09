from windfreak import SynthHD
from pylabnet.utils.logging.logger import LogHandler


class Driver():
    POWER_RANGE = [-40, 18]    # acceptable power range in dBm
    #POWER_PRECISION = 2 # number of digits of precision for power
    FREQ_RANGE = [10e6, 24e9]    # acceptable frequency range in Hz

    def __init__(self, device_port, logger):
        """ Instantiate driver class, connects to device

        :param device_port: port where device is located (COM port),
            can be found with pyvisa.ResourceManager.list_resources()
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger=logger)
        self.synth = SynthHD(device_port)
        self.synth.init()

    def set_power(self, power, channel=None):
        """ Sets power of MW source

        :param power: (float) output power to set in dBm
        """
        # Check for valid range
        if power < self.POWER_RANGE[0] or power > self.POWER_RANGE[1]:
            self.log.warn(
                f'Warning, power outside acceptable range {self.POWER_RANGE}. '
                f'Output power was not updated.'
            )
        # Set power
        else:
            if channel == 'A':
                self.synth[0].power = power
            elif channel == 'B':
                self.synth[1].power = power
            else:
                self.log.warn('Warning: no channel selected, select A or B')

    def set_freq(self, freq, channel=None):
        """ Sets power of MW source

        :param freq: (float) output frequency in Hz
        """

        # Check for valid range
        if freq < self.FREQ_RANGE[0] or freq > self.FREQ_RANGE[1]:
            self.log.warn(
                f'Warning, frequency outside acceptable range {self.FREQ_RANGE}. '
                f'Output frequency was not updated.'
            )
        # Set freq
        else:
            if channel == 'A':
                self.synth[0].frequency = freq
            elif channel == 'B':
                self.synth[1].frequency = freq
            else:
                self.log.warn('Warning: no channel selected, select A or B')

    def set_trigger(self, trigger_mode=None):
        """ Sets power of MW source

        :param trigger mode: (str)
            'disabled',
            'full frequency sweep',
            'single frequency step',
            'stop all',
            'rf enable',
            'remove interrupts',
            'reserved',
            'reserved',
            'am modulation',
            'fm modulation',
        """

        # Set trigger mode
        self.log.warn('previous trigger mode: ' + str(self.synth.trigger_mode))
        self.synth.trigger_mode = trigger_mode
        self.log.info('now, the trigger mode: ' + self.synth.trigger_mode)

    def set_reference_mode(self, arg=None):
        """Set frequency reference mode.

        Args:
            arg (str): mode
        """

        # Set reference mode
        if(arg is not None):
            self.synth.reference_mode = arg
            self.log.warn('reference mode.: ' + str(self.synth.reference_mode))
        else:
            self.log.warn('arg cannot be None')

    def set_external_reference_frequency(self, value=None):
        """Set reference frequency in Hz.

        Args:
            value (float / int): frequency in Hz
        """

        # Set reference mode
        if(value is not None):
            self.synth.reference_frequency = value
            self.log.warn('reference frequency (external).: ' + str(self.synth.reference_frequency))
        else:
            self.log.warn('value cannot be None')

    def output_on(self, channel=None):
        """ Turn output on """

        if channel == 'A':
            self.synth[0].enable = True
        elif channel == 'B':
            self.synth[1].enable = True
        else:
            self.log.warn('Warning: no channel selected, select A or B')

        self.log.info('MW output turned on')

    def output_off(self, channel=None):
        """ Turn output off """

        if channel == 'A':
            self.synth[0].enable = False
        elif channel == 'B':
            self.synth[1].enable = False
        else:
            self.log.warn('Warning: no channel selected, select A or B')

        self.log.info('MW output turned off')
