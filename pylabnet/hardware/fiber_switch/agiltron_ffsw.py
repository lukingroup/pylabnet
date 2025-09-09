from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver():

    def __init__(self, device_id, num_chs, logger):
        """ Instantiate driver class, connects to device

        :param device_id: USB-address of the device,
            can be found with pyvisa.ResourceManager.list_resources(),
            e.g. 'ASRL4::INSTR'
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()
        self.device_id = device_id
        self.num_chs = num_chs

        try:
            self.device = self.rm.open_resource(device_id)
            self.log.info(f'Successfully connected to {device_id}')
        except VisaIOError:
            self.log.error(f'Connection to {device_id} failed')
            raise VisaIOError

    def _valid_ch(self, ch):
        """ Check if target channel is valid.
        :param ch: (int) channel number to be controlled
        """
        if (ch < 0) or (ch >= self.num_chs):
            self.log.warn(f"Invalid channel {ch} received.")
            return False
        else:
            return True

    def set_output(self, ch):
        """ Set switch to target output channel.
        :param ch: (int) switch channel number to be connected
        """
        if self._valid_ch(ch):
            # b'\x01\x12\x00\x01'
            # <Addr> <Code> <Dx> <Dy>
            # Addr: Module address, default is 1
            # Code: Command 12 sets switch to status N = <Dx><Dy>
            cmd = [1, 0x12, 0, ch]
            self.device.write_raw(bytes(cmd))
            self.log.info(f'Sent command {cmd}')
            self.log.info(f'Switch set to output {ch}')
