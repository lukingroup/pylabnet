from interface.mw_src import MWSrcInterface
from utils.logging.logger import LogHandler
import visa


class RSsmcMWSrc(MWSrcInterface):

    def __init__(self, addr_str, logger=None):

        self.log = LogHandler(logger=logger)

        # Connect to the device
        self.rm = visa.ResourceManager()
        try:
            self._dev = self.rm.open_resource(addr_str)
        except Exception as exc_obj:
            self.log.exception(
                msg_str='Could not connect to the address >>{}<<. \n'.format(addr_str)
            )
            raise exc_obj

        # Log confirmation info message
        id_str = self._dev.query('*IDN?').replace(',', ' ')
        id_str = id_str.strip('\n')
        self.log.info(
            msg_str='{} initialised and connected.'.format(id_str)
        )

        # Reset device
        self.reset()

        # Error check
        self._er_chk()

    def activate_interface(self):
        return self.reset()

    def reset(self):
        # Reset
        self._cmd_wait('*RST')
        # Clear status register
        self._cmd_wait('*CLS')

        return 0

    def on(self):
        return self._cmd_wait(
            cmd_str=':OUTP:STAT ON'
        )

    def off(self):
        return self._cmd_wait(
            cmd_str=':OUTP:STAT OFF'
        )

    def get_status(self):
        status = int(
            self._dev.query('OUTP:STAT?')
        )
        return status

    def

    def get_mode(self):
        mode_str = self._dev.query(':FREQ:MODE?').strip('\n').lower()

        if 'cw' in mode_str:
            return 'cw'
        elif 'swe' in mode_str:
            return 'sweep'
        else:
            msg_str = 'get_mode(): unknown mode string {} was returned'
            self.log.error(msg_str=msg_str)
            raise CWMWError(msg_str)

    def set_mode(self, mode_str):
        if mode_str == 'cw':
            self._cmd_wait(':FREQ:MODE CW')
        elif mode_str == 'sweep':
            self._cmd_wait(':FREQ:MODE SWEEP')
        else:
            msg_str = 'set_mode(): invalid mode string "{}" \n' \
                      'Valid values are "cw" and "sweep"' \
                      ''.format(mode_str)

            self.log.error(msg_str=msg_str)
            raise CWMWError(msg_str)

        return self.get_mode()

    def get_pwr(self):
        return float(self._dev.query(':POW?'))

    def set_pwr(self, pwr):
        self._cmd_wait(':POW {0:f}'.format(pwr))

        return self.get_pwr()

    def get_freq(self):
        return float(self._dev.query(':FREQ?'))

    def set_freq(self, freq):
        self._cmd_wait(
            ':FREQ {0:f}'.format(freq)
        )
        return self.get_freq()

    def set_freq_swp(self, start, stop, n_pts):
        step = (stop - start) / (n_pts - 1)

        self._dev.write(':SWE:MODE STEP')
        self._dev.write(':SWE:SPAC LIN')
        self._dev.write('*WAI')
        self._dev.write(':FREQ:START {0:f}'.format(start))
        self._dev.write(':FREQ:STOP {0:f}'.format(stop))
        self._dev.write(':SWE:STEP:LIN {0:f}'.format(step))
        self._dev.write('*WAI')

        # Error check
        self._er_chk()

        return self.get_freq_swp()

    def get_freq_swp(self):
        start = float(self._dev.query(':FREQ:STAR?'))
        stop = float(self._dev.query(':FREQ:STOP?'))
        step = float(self._dev.query(':SWE:STEP?'))

        n_pts = int((stop - start) / step) + 1

        ret_dict = dict(
            start=start,
            stop=stop,
            n_pts=n_pts
        )

        return ret_dict

    def _er_chk(self):
        # Block command queue until all previous commands are complete
        self._dev.write('*WAI')
        # Block Python process until all previous commands are complete
        self._dev.query('*OPC?')

        # Read all messages
        out_str = self._dev.query(':SYSTem:ERRor:ALL?')
        out_str += ','
        out_str += self._dev.query('SYST:SERR?')

        out_str = out_str.replace('\n', '')
        out_str = out_str.replace('\r', '')
        out_str = out_str.replace('"', '')

        out_list = out_str.split(',')

        # Collect all warns and errors
        er_list = []
        warn_list = []

        msg_n = int(len(out_list) / 2)

        for idx in range(msg_n):
            msg_code = int(out_list[2 * idx])

            if msg_code == 0:
                # No error
                continue

            elif msg_code > 0:
                # Warning
                warn_list.append(out_list[2 * idx + 1])

            else:
                # Error
                er_list.append(out_list[2 * idx + 1])

        # Construct Warn message string
        if len(warn_list) > 0:
            warn_str = ''
            for warn in warn_list:
                warn_str += (warn + ' \n')
            warn_str = warn_str.rstrip('\n')
            self.log.warn(msg_str=warn_str)

        # Construct Error message string
        if len(er_list) > 0:
            er_str = ''
            for er in er_list:
                er_str += (er + ' \n')
            er_str = er_str.rstrip('\n')
            self.log.error(msg_str=er_str)
            raise CWMWError(er_str)

        return 0

    def _cmd_wait(self, cmd_str):
        """Writes the command in command_str via resource manager
        and waits until the device has finished processing it.

        @param cmd_str: The command to be written
        """

        self._dev.write(cmd_str)

        # Block command queue until cmd_str execution is complete
        self._dev.write('*WAI')
        # Block Python process until cmd_str execution is complete
        self._dev.query('*OPC?')

        # Error check
        self._er_chk()

        return 0


class CWMWError(Exception):
    pass
