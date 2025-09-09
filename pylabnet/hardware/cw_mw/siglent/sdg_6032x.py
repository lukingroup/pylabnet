from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver():

    VALID_CHS = [1, 2]
    FREQ_RANGE = [0, 350E6]

    def __init__(self, device_id, logger):
        """ Instantiate driver class, connects to device

        :param device_id: USB-address of the device,
            can be found with pyvisa.ResourceManager.list_resources(),
            e.g. 'USB0::0xF4EC::0x1101::SDG6XFCD6R1212::INSTR'
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()
        self.device_id = device_id

        try:
            self.device = self.rm.open_resource(device_id)
            device_reply = self.device.query('*IDN?')
            self.log.info(f'Successfully connected to {device_id}')
            self.log.info(f'Device reply: {device_reply}')
        except VisaIOError:
            self.log.error(f'Connection to {device_id} failed')
            raise VisaIOError

    def _valid_ch(self, ch):
        """ Check if target channel is valid.
        :param ch: (int) channel number to be controlled
        """
        if ch not in self.VALID_CHS:
            self.log.warn(f"Invalid channel {ch} received.")
            return False
        else:
            return True

    def _valid_freq(self, freq):
        """ Check if target frequency is valid.
        :param freq: (float) output frequency in Hz
        """
        if freq < self.FREQ_RANGE[0] or freq > self.FREQ_RANGE[1]:
            self.log.warn(
                f'Warning, frequency outside acceptable range {self.FREQ_RANGE}. '
                f'Output frequency was not updated.'
            )
            return False
        else:
            return True

    def reset(self):
        """ Fully resets the device. """
        self.device.write(f'*RST')
        self.log.info(f'Device {self.device_id} has been reset.')

    def output_on(self, ch):
        """ Turn output of target channel on.
        :param ch: (int) channel number to be controlled
        """

        if self._valid_ch(ch):
            self.device.write(f'C{ch}:OUTPUT ON')
            self.log.info(f'MW output {ch} turned on')

    def output_off(self, ch):
        """ Turn output of target channel off.
        :param ch: (int) channel number to be controlled
        """

        if self._valid_ch(ch):
            self.device.write(f'C{ch}:OUTPUT OFF')
            self.log.info(f'MW output {ch} turned off')

    def set_amp_vpp(self, ch, amp_vpp):
        """ Sets amplitude of target channel.
        :param ch: (int) channel number to be controlled
        :param amp_vpp: (float) output waveform amplitude (pk-pk) in V
        """

        if self._valid_ch(ch):
            self.device.write(f"C{ch}:BASIC_WAVE AMP, {amp_vpp}")
            self.log.info(f'Set MW output {ch} power to {amp_vpp} Vpp')

    def set_freq(self, ch, freq):
        """ Sets frequency of target channel.
        :param ch: (int) channel number to be controlled
        :param freq: (float) output frequency in Hz
        """

        if self._valid_ch(ch) and self._valid_freq(freq):
            freq = int(freq)
            self.device.write(f'C{ch}:BASIC_WAVE FRQ, {freq}')
            self.log.info(f'Set MW output {ch} freq to {freq} Hz')
