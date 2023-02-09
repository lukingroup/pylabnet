from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.mw_src import MWSrcInterface, MWSrcError
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Driver(MWSrcInterface):
    """Adapted from Qudi <https://github.com/Ulm-IQO/qudi/>
    """

    def __init__(self, addr_str, logger=None):

        self.log = LogHandler(logger=logger)

        # Connect to the device
        self.rm = ResourceManager()
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

    def reset(self):
        # Reset
        self._cmd_wait('*RST')
        # Clear status register
        self._cmd_wait('*CLS')

        return 0

    def activate_interface(self):

        # Store hardware settings which are not controlled by logic,
        # to restore them after reset()
        # [logic does not know anything about this params, so it should not
        # introduce any changes to them by calling activate_interface()].
        tmp_trig_dict = self.get_trig()

        # Reset device
        self.reset()

        # Restore hardware settings which are not controlled by logic
        # but were changed by self._dev.reset()

        self.set_trig(
            src_str=tmp_trig_dict['src_str'],
            slope_str=tmp_trig_dict['slope_str']
        )

        return 0

    # Output control

    def on(self):

        if self.get_mode() == 'sweep':
            self.reset_swp_pos()

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

    # Power

    def get_pwr(self):
        return float(self._dev.query(':POW?'))

    def set_pwr(self, pwr):
        self._cmd_wait(':POW {0:f}'.format(pwr))

        return self.get_pwr()

    # Frequency

    def get_freq(self):
        mode = self.get_mode()

        if mode == 'cw':
            ret_val = float(self._dev.query(':FREQ?'))

        elif mode == 'sweep':
            start = float(self._dev.query(':FREQ:STAR?'))
            stop = float(self._dev.query(':FREQ:STOP?'))
            step = float(self._dev.query(':SWE:STEP?'))

            n_pts = int((stop - start) / step) + 2

            ret_val = dict(
                start=start,
                stop=stop,
                n_pts=n_pts
            )

        else:
            raise MWSrcError(
                'get_freq(): got unknown mode {}'.format(mode)
            )

        return ret_val

    def set_freq(self, freq):

        if self.get_status() == 1:
            self.off()

        # Activate CW mode
        self._cmd_wait(':FREQ:MODE CW')

        # Set CW frequency
        self._cmd_wait(':FREQ {0:f}'.format(freq))

        return self.get_freq()

    def set_freq_swp(self, start, stop, n_pts):

        if self.get_status() == 1:
            self.off()

        # Set mode to Sweep
        self._cmd_wait(':FREQ:MODE SWEEP')

        # Set frequency sweep
        step = (stop - start) / (n_pts - 1)

        self._cmd_wait(':SWE:MODE STEP')
        self._cmd_wait(':SWE:SPAC LIN')
        self._cmd_wait(':FREQ:START {0:f}'.format(start))
        self._cmd_wait(':FREQ:STOP {0:f}'.format(stop))
        self._cmd_wait(':SWE:STEP:LIN {0:f}'.format(step))

        return self.get_freq()

    def reset_swp_pos(self):
        """Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """

        self._cmd_wait(':ABOR:SWE')
        return 0

    def get_mode(self):

        mode_str = self._dev.query(':FREQ:MODE?').strip('\n').lower()

        if 'cw' in mode_str:
            return 'cw'
        elif 'swe' in mode_str:
            return 'sweep'
        else:
            msg_str = 'get_mode(): unknown mode string {} was returned'
            self.log.error(msg_str=msg_str)
            raise MWSrcError(msg_str)

    # Technical methods

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
            raise MWSrcError(er_str)

        return 0

    def get_trig(self):

        #
        # Get trigger source
        #

        src_str = self._dev.query('TRIG:FSW:SOUR?')

        if 'EXT' in src_str:
            src_str = 'ext'
        elif 'AUTO' in src_str:
            src_str = 'int'
        else:
            msg_str = 'get_trig(): unknown trigger source was returned "{}" \n' \
                      ''.format(src_str)
            self.log.error(msg_str=msg_str)
            raise MWSrcError(msg_str)

        #
        # Get edge slope
        #

        slope_str = self._dev.query(':TRIG1:SLOP?')

        if 'POS' in slope_str:
            slope_str = 'r'
        elif 'NEG' in slope_str:
            slope_str = 'f'
        else:
            msg_str = 'get_trig(): unknown slope was returned "{}" \n' \
                      ''.format(slope_str)
            self.log.error(msg_str=msg_str)
            raise MWSrcError(msg_str)

        return dict(src_str=src_str, slope_str=slope_str)

    def set_trig(self, src_str='ext', slope_str='r'):

        if self.get_status() == 1:
            self.off()

        #
        # Set trigger source
        #

        if src_str == 'ext':
            src_str = 'EXT'
        elif src_str == 'int':
            src_str = 'AUTO'
        else:
            msg_str = 'set_trig(): unknown trigger source  "{}" \n' \
                      'Valid values are "ext" - external, "int" - internal' \
                      ''.format(src_str)
            self.log.error(msg_str=msg_str)
            raise MWSrcError(msg_str)

        self._cmd_wait('TRIG:FSW:SOUR {}'.format(src_str))

        #
        # Set trigger edge
        #

        if slope_str == 'r':
            edge = 'POS'
        elif slope_str == 'f':
            edge = 'NEG'
        else:
            msg_str = 'set_trig(): invalid argument slope_str={} \n' \
                      'Valid values are: "r" - raising, "f" - falling' \
                      ''.format(slope_str)
            self.log.error(msg_str=msg_str)
            raise ValueError(msg_str)

        self._cmd_wait(':TRIG1:SLOP {0}'.format(edge))

        return self.get_trig()

    def force_trig(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        self._cmd_wait('*TRG')

        return 0
