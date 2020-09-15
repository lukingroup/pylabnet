from telnetlib import Telnet
from copy import deepcopy

from pylabnet.utils.logging.logger import LogHandler


class DLC_Pro:
    """ Driver class for Toptica DLC Pro """

    def __init__(self, host, port=1998, logger=None):
        """ Instantiates DLC_Pro object

        :param host: (str) hostname of laser (IP address)
        :param port: (int) port number, toptica defaults to 1998
        :param logger: (LogClient)
        """

        self.host = host
        self.port = port
        self.log = LogHandler(logger)
        self.dlc = None

        # Check connection
        try:

            # Check laser connection
            self.dlc = Telnet(host=self.host, port=self.port)
            self.dlc.read_until(b'>', timeout=1)
            self.dlc.write(b"(param-disp 'laser1:dl:type)\n")
            laser_type = self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1]
            self.dlc.write(b"(param-disp 'laser1:dl:serial-number)\n")
            serial = int(self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1])
            self.log.info(f'Connected to Toptica {laser_type}, S/N {serial}')

        except ConnectionRefusedError:
            self.log.error('Could not connect to Toptica DLC Pro at '
                           f'IP address: {self.host}, port: {self.port}')

    def is_laser_on(self):
        """ Checks if the laser is on or off

        :return: (bool) whether or not emission is on or off
        """

        self.dlc.write(b"(param-disp 'laser1:dl:cc:emission)\n")
        result = self.dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')
        status = result[1]
        if status == 't':
            return True
        elif status == 'f':
            return False
        else:
            self.log.warn('Could not determine properly whether the laser is on or off')
            return False

    def turn_on(self):
        """ Turns on the laser """

        # Check if laser is on already
        if self.is_laser_on():
            self.log.info('Laser is already on')
        else:
            self.dlc.write(b"(param-set! 'laser1:dl:cc:enabled #t)\n")
            self.dlc.read_until(b'>', timeout=1)
            if self.is_laser_on():
                self.log.info('Turned on Toptica DL-Pro laser')
            else:
                self.log.warn('Laser could not be turned on. Physical emission button may need to be pressed')

    def turn_off(self):
        """ Turns off the laser """

        if self.is_laser_on():
            self.dlc.write(b"(param-set! 'laser1:dl:cc:enabled #f)\n")
            self.dlc.read_until(b'>', timeout=1)
            if self.is_laser_on():
                self.log.warn('Failed to verify that DL-Pro laser turned off')
            else:
                self.log.info('Turned off Toptica DL-Pro laser')
        else:
            self.log.info('Laser is already off')

    def voltage(self):
        """ Gets current voltage on laser piezo

        :return: (float) current voltage on piezo
        """

        self.dlc.write(b"(param-disp 'laser1:dl:pc:voltage-set)\n")
        voltage = float(self.dlc.read_until(b'>', timeout=1).split()[-3])

        return voltage

    def set_voltage(self, voltage):
        """ Sets voltage to the piezo

        :param voltage: (float) voltage to set
        """

        v = deepcopy(voltage)
        write_data = f"(param-set! 'laser1:dl:pc:voltage-set {v})\n"
        write_data = write_data.encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def current_sp(self):
        """ Gets current setpoint

        :return: (float) value of current setpoint
        """

        self.dlc.write(b"(param-disp 'laser1:dl:cc:current-set)\n")
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def current_act(self):
        """ Gets measured current

        :return: (float) value of actual current
        """

        self.dlc.write(b"(param-disp 'laser1:dl:cc:current-act)\n")
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])
    
    def set_current(self, current):
        """ Sets the current to desired value
        
        :param current: (float) value of current to set as setpoint
        """

        c = deepcopy(current)
        write_data = f"(param-set! 'laser1:dl:cc:current-set {c})\n"
        write_data = write_data.encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def temp_sp(self):
        """ Gets temperature setpoint

        :return: (float) value of temperature setpoint
        """

        self.dlc.write(b"(param-disp 'laser1:dl:tc:temp-set)\n")
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def temp_act(self):
        """ Gets actual DL temp

        :return: (float) value of temperature
        """

        self.dlc.write(b"(param-disp 'laser1:dl:tc:temp-act)\n")
        return float(self.dlc.read_until(b'>', timeout=1).split()[-3])

    def set_temp(self, temp):
        """ Sets the current to desired value
        
        :param temp: (float) value of temperature to set to in Celsius
        """

        t = deepcopy(temp)
        write_data = f"(param-set! 'laser1:dl:tc:temp-set {t})\n"
        write_data = write_data.encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def configure_scan(self, offset=65, amplitude=100, frequency=0.2):
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
            write_data = f"(param-set! 'laser1:scan:offset {o})\n"
            write_data = write_data.encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            a = deepcopy(amplitude)
            write_data = f"(param-set! 'laser1:scan:amplitude {a})\n"
            write_data = write_data.encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            f = deepcopy(frequency)
            write_data = f"(param-set! 'laser1:scan:frequency {f})\n"
            write_data = write_data.encode('utf')
            self.dlc.write(write_data)
            self.dlc.read_until(b'>', timeout=1)

            self.log.info(f'Scan with offset {o}, amplitude {a}, frequency {f} successfully configured.')

    def start_scan(self):
        """ Starts a piezo scan """

        write_data = f"(param-set! 'laser1:scan:enabled #t)\n"
        write_data = write_data.encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)

    def stop_scan(self):
        """ Stops piezo scan """

        write_data = f"(param-set! 'laser1:scan:enabled #f)\n"
        write_data = write_data.encode('utf')
        self.dlc.write(write_data)
        self.dlc.read_until(b'>', timeout=1)
