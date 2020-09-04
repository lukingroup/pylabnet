from telnetlib import Telnet

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

        # Check connection
        try:

            # Check laser connection
            with Telnet(host=self.host, port=self.port) as dlc:
                dlc.read_until(b'>', timeout=1)
                dlc.write(b"(param-disp 'laser1:dl:type)\n")
                laser_type = dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1]
                dlc.write(b"(param-disp 'laser1:dl:serial-number)\n")
                serial = int(dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1:-1])
            self.log.info(f'Connected to Toptica {laser_type}, S/N {serial}')

        except ConnectionRefusedError:
            self.log.error('Could not connect to Toptica DLC Pro at '
                           f'IP address: {self.host}, port: {self.port}')

    def is_laser_on(self):
        """ Checks if the laser is on or off

        :return: (bool) whether or not emission is on or off
        """

        with Telnet(host=self.host, port=self.port) as dlc:
            dlc.read_until(b'>', timeout=1)

            dlc.write(b"(param-disp 'laser1:dl:cc:enabled)\n")
            status = dlc.read_until(b'>', timeout=1).split()[-3].decode('utf')[1]
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
            with Telnet(host=self.host, port=self.port) as dlc:
                dlc.read_until(b'>', timeout=1)
                dlc.write(b"(param-set! 'laser1:dl:cc:enabled #t)\n")
                dlc.read_until(b'>', timeout=1)
            if self.is_laser_on():
                self.log.info('Turned on Toptica DL-Pro laser')
            else:
                self.log.warn('Failed to verify that DL-Pro laser turned on')

    def turn_off(self):
        """ Turns off the laser """

        if self.is_laser_on():
            with Telnet(host=self.host, port=self.port) as dlc:
                dlc.read_until(b'>', timeout=1)
                dlc.write(b"(param-set! 'laser1:dl:cc:enabled #f)\n")
                dlc.read_until(b'>', timeout=1)
            if self.is_laser_on():
                self.log.warn('Failed to verify that DL-Pro laser turned on')
            else:
                self.log.info('Turned on Toptica DL-Pro laser')
        else:
            self.log.info('Laser is already off')

    def voltage(self):
        """ Gets current voltage on laser piezo

        :return: (float) current voltage on piezo
        """

        with Telnet(host=self.host, port=self.port) as dlc:
            dlc.read_until(b'>', timeout=1)
            dlc.write(b"(param-disp 'laser1:dl:pc:voltage-set)\n")
            voltage = float(dlc.read_until(b'>', timeout=1).split()[-3])

        return voltage

    def set_voltage(self, voltage):
        """ Sets voltage to the piezo

        :param voltage: (float) voltage to set
        """

        with Telnet(host=self.host, port=self.port) as dlc:
            dlc.read_until(b'>', timeout=1)
            dlc.write(f"(param-set! 'laser1:dl:pc:voltage-set {voltage})\n".encode('utf'))
            dlc.read_until(b'>', timeout=1)
            