from telnetlib import Telnet
from copy import deepcopy

from pylabnet.utils.logging.logger import LogHandler


class DLC_Pro:
    """ Driver class for Toptica DLC Pro """

    def __init__(self, host, port=1998, logger=None, num_lasers=2):
        """ Instantiates DLC_Pro object

        :param host: (str) hostname of laser (IP address)
        :param port: (int) port number, toptica defaults to 1998
        :num_lasers: Number of installed lasers
        :param logger: (LogClient)
        """

        self.host = host
        self.port = port
        self.log = LogHandler(logger)
        self.dlc = None
        self.laser_nums = range(1, num_lasers+1)

        # Check connection
        try:

            # Check laser connection
            self.dlc = Telnet(host=self.host, port=self.port)
            self.dlc.read_until(b'>', timeout=1)

            for laser_num in self.laser_nums:
                self._check_laser_connection(laser_num)

        except ConnectionRefusedError:
            self.log.error('Could not connect to Toptica DLC Pro at '
                           f'IP address: {self.host}, port: {self.port}')



    def _check_laser_connection(self, laser_num=1):
        """ Read out laser number

        :laser_num: (int) 1 or 2, indicating laser 1 or laser 2.
        """
        self.dlc.read_until(b'>', timeout=1)
        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:type)\n".encode('utf'))
        laser_type = self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1]
        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:serial-number)\n".encode('utf'))
        serial = int(self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1])
        self.log.info(f'Connected to Toptica {laser_type} {laser_num}, S/N {serial}')


    def is_laser_on(self, laser_num=1):
        """ Checks if the laser is on or off

        :return: (bool) whether or not emission is on or off
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:cc:emission)\n".encode('utf'))
        result = self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')
        status = result[1]
        if status == 't':
            return True
        elif status == 'f':
            return False
        else:
            self.log.warn('Could not determine properly whether the laser is on or off')
            return False

    def turn_on(self, laser_num=1):
        """ Turns on the laser """

        # Check if laser is on already
        if self.is_laser_on(laser_num):
            self.log.info(f'Laser {laser_num} is already on')
        else:
            self.dlc.write(f"(param-set! 'laser{laser_num}:dl:cc:enabled #t)\n".encode('utf'))
            self.dlc.read_until(b'>', timeout=1)
            if self.is_laser_on(laser_num):
                self.log.info(f'Turned on Toptica DL-Pro laser {laser_num}')
            else:
                self.log.warn(f'Laser {laser_num} could not be turned on. Physical emission button may need to be pressed')

    def turn_off(self, laser_num=1):
        """ Turns off the laser """

        if self.is_laser_on(laser_num):
            self.dlc.write(f"(param-set! 'laser{laser_num}:dl:cc:enabled #f)\n".encode('utf'))
            self.dlc.read_until(b'>', timeout=1)
            if self.is_laser_on(laser_num):
                self.log.warn(f'Failed to verify that DL-Pro laser {laser_num} turned off')
            else:
                self.log.info(f'Turned off Toptica DL-Pro laser {laser_num}')
        else:
            self.log.info(f'Laser {laser_num} is already off')

    def voltage(self, laser_num=1):
        """ Gets current voltage on laser piezo

        :return: (float) current voltage on piezo
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:pc:voltage-set)\n".encode('utf'))
        voltage = float(self.dlc.read_until(b'>', timeout=1).split()[-3])

        return voltage

    def set_voltage(self, voltage, laser_num=1):
        """ Sets voltage to the piezo

        :param voltage: (float) voltage to set
        """

        v = deepcopy(voltage)
        write_data = f"(param-set! 'laser{laser_num}:dl:pc:voltage-set {v})\n".encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def current_sp(self, laser_num=1):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:cc:current-set)\n".encode('utf'))
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def current_act(self, laser_num=1):
        """ Gets measured current

        :return: (float) value of actual current
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:cc:current-act)\n".encode('utf'))
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def set_current(self, current, laser_num=1):
        """ Sets the current to desired value

        :param current: (float) value of current to set as setpoint
        """

        c = deepcopy(current)
        write_data = f"(param-set! 'laser{laser_num}:dl:cc:current-set {c})\n".encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def temp_sp(self, laser_num=1):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:tc:temp-set)\n".encode('utf'))
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def temp_act(self, laser_num=1):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        self.dlc.write(f"(param-disp 'laser{laser_num}:dl:tc:temp-act)\n".encode('utf'))
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def set_temp(self, temp, laser_num=1):
        """ Sets the current to desired value

        :param temp: (float) value of temperature to set to in Celsius
        """

        t = deepcopy(temp)
        write_data = f"(param-set! 'laser{laser_num}:dl:tc:temp-set {t})\n".encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def configure_scan(self, offset=65, amplitude=100, frequency=0.2, laser_num=1):
        """ Sets the scan parameters for piezo scanning

        :param offset: (float) scan offset (center value) in volts (between 0 and 130)
        :param amplitude: (float) scan amplitude (peak to peak) in volts
        :param frequency: (Float) scan frequency in Hz
        """

        # Check that parameters are within range
        if (offset + (amplitude/2) > 130) or (offset - (amplitude/2) < -1):
            self.log.warn('Warning, invalid scan parameters set.'
                          'Make sure voltages are between -1 and 130 V')

        else:
            o = deepcopy(offset)
            write_data = f"(param-set! 'laser{laser_num}:scan:offset {o})\n".encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            a = deepcopy(amplitude)
            write_data = f"(param-set! 'laser{laser_num}:scan:amplitude {a})\n".encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            f = deepcopy(frequency)
            write_data = f"(param-set! 'laser{laser_num}:scan:frequency {f})\n".encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            self.log.info(f'Scan with offset {o}, amplitude {a}, frequency {f} for laser {laser_num} successfully configured.')

    def start_scan(self, laser_num=1):
        """ Starts a piezo scan """

        write_data = f"(param-set! 'laser{laser_num}:scan:enabled #t)\n".encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def stop_scan(self, laser_num=1):
        """ Stops piezo scan """

        write_data = f"(param-set! 'laser{laser_num}:scan:enabled #f)\n".encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)
