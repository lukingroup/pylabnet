"""Adapted from Qudi <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import time
from utils.logging.logger import LogHandler


class RSsmc:
    """ Hardware file to control a R&S SMBV100A microwave device.
    """

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

    # def disconnect(self):
    #     self.rm.close()
    #     return 0

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

    def reset(self):
        # Reset
        self._cmd_wait('*RST')
        # Clear status register
        self._cmd_wait('*CLS')

        return 0

    def get_status(self):
        """Gets the current status of the MW source

        @return int: status:
                    0 - idle
                    1 - running
                    Exception is produced in the case of error
        """

        status = int(
            self._dev.query('OUTP:STAT?')
        )

        return status

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
        """
        Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        # This case works for cw AND sweep mode
        return float(self._dev.query(':POW?'))

    def get_freq(self):
        """Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """

        mode = self.get_mode()

        if mode == 'cw':
            return_val = float(self._dev.query(':FREQ?'))

        elif mode == 'sweep':
            start = float(self._dev.query(':FREQ:STAR?'))
            stop = float(self._dev.query(':FREQ:STOP?'))
            step = float(self._dev.query(':SWE:STEP?'))
            return_val = [start, stop, step]

        else:
            raise CWMWError(
                'get_freq(): got unknown mode {}'.format(mode)
            )

        return return_val

    def off(self):
        """Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """

        status = self.get_status()

        if status == 0:
            return 0

        self._cmd_wait('OUTP:STAT OFF')

        while int(self._dev.query('OUTP:STAT?')) != 0:
            time.sleep(0.2)

        return 0

    def set_cw(self, freq=None, pwr=None):
        """Configures the device for cw-mode and optionally sets frequency and/or power

        @param float freq: frequency to set in Hz
        @param float pwr: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """

        is_running = self.get_status()
        mode = self.get_mode()

        if is_running:
            self.off()

        # Activate CW mode
        if mode != 'cw':
            self._cmd_wait(':FREQ:MODE CW')

        # Set CW frequency
        if freq is not None:
            self._cmd_wait(':FREQ {0:f}'.format(freq))

        # Set CW power
        if pwr is not None:
            self._cmd_wait(':POW {0:f}'.format(pwr))

        # Return actually set values
        actual_freq = self.get_freq()
        actual_power = self.get_pwr()
        mode = self.get_mode()

        return actual_freq, actual_power, mode

    def cw_on(self):
        """Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """

        is_running = self.get_status()
        current_mode = self.get_mode()

        if is_running:
            if current_mode == 'cw':
                return 0
            else:
                self.off()

        if current_mode != 'cw':
            self.set_mode(mode_str='cw')

        self._cmd_wait(':OUTP:STAT ON')

        while not self.get_status():
            time.sleep(0.2)

        return 0

    def set_sweep(self, start=None, stop=None, n_pts=None, power=None):
        """Configures the device for sweep-mode and
        optionally sets frequency start/stop/step and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """

        is_running = self.get_status()
        mode = self.get_mode()

        if is_running:
            self.off()

        if mode != 'sweep':
            self._cmd_wait(':FREQ:MODE SWEEP')

        if (start is not None) and (stop is not None) and (n_pts is not None):
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

        if power is not None:
            self._dev.write(':POW {0:f}'.format(power))
            self._dev.write('*WAI')

            # Error check
            self._er_chk()

        self._cmd_wait('TRIG:FSW:SOUR EXT')

        # Return actual values
        start, stop, step = self.get_freq()
        power = self.get_pwr()
        mode = self.get_mode()

        return start, stop, step, power, mode

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """

        is_running = self.get_status()
        current_mode = self.get_mode()

        if is_running:
            if current_mode == 'sweep':
                return 0
            else:
                self.off()

        if current_mode != 'sweep':
            self.set_mode(mode_str='sweep')

        self._cmd_wait(':OUTP:STAT ON')

        while not self.get_status():
            time.sleep(0.2)

        return 0

    def reset_sweeppos(self):
        """Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """

        self._cmd_wait(':ABOR:SWE')
        return 0

    def set_ext_trig(self, edge_str):
        """ Set the external trigger for this device with proper polarization.

        @param edge_str: 'r' - rising edge, 'f' - falling edge

        @return (str): actual trigger edge
        """

        is_running = self.get_status()

        if is_running:
            self.off()

        if edge_str == 'r':
            edge = 'POS'
        elif edge_str == 'f':
            edge = 'NEG'
        else:
            msg_str = 'set_ext_trig(): invalid argument edge_str={} \n' \
                      'Valid values are: "r" - raising, "f" - falling' \
                      ''.format(edge_str)

            self.log.error(msg_str=msg_str)
            raise ValueError(msg_str)

        self._cmd_wait(':TRIG1:SLOP {0}'.format(edge))

        polarity = self._dev.query(':TRIG1:SLOP?')
        if 'NEG' in polarity:
            return 'f'
        elif 'POS' in polarity:
            return 'r'
        else:
            msg_str = 'set_ext_trig(): device returned unknown edge type {}' \
                      ''.format(polarity)
            self.log.error(msg_str=msg_str)
            raise CWMWError(msg_str)

    def force_trig(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        self._cmd_wait('*TRG')

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
            raise CWMWError(er_str)

        return 0


class CWMWError(Exception):
    pass
