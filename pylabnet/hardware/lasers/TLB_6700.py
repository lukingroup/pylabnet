import sys
import clr
from System.Text import StringBuilder
import time
import numpy as np

from pylabnet.utils.logging.logger import LogHandler


class Driver:
    """ Driver class for Toptica DLC Pro """

    def __init__(self, device_id, New_Focus_program_path, product_id=4106, logger=None):
        """ Instantiates DLC_Pro object

        NOTE: for this driver to work, you must have installed the New Focus Laser Tuning
        application: https://www.newport.com/f/velocity-wide-&-fine-tunable-lasers on your computer

        :param host: (str) hostname of laser (IP address)
        :param device_id (str): DeviceKey or name of device, of form '6700 SNxxxxx'
        :param product_id (int): ProductID of device, Velocity defaults to 4106
        :param New_Focus_program_path (str): path to where the New Focus Driver has been installed (location of UsbDllWrap.dll file)
        :param logger: (LogClient)
        """

        self.device_id = device_id
        self.product_id = product_id
        self.New_Focus_program_path = New_Focus_program_path
        self.log = LogHandler(logger)
        self.tlb = None

        self._buff = StringBuilder(64)

        sys.path.append(self.New_Focus_program_path)
        clr.AddReference('UsbDllWrap')
        import Newport

        # Try connecting to laser
        try:

            # Check laser connection
            self.tlb = Newport.USBComm.USB()
            self.tlb_open()
            self.query_laser_id()

            self.set_remote_control()

        except ConnectionRefusedError:
            self.log.error('Could not connect to Velocity at '
                           f'Device ID: {self.device_id}, product ID: {self.product_id}')

    def tlb_open(self):
        self.tlb.OpenDevices(self.product_id, True)

    def tlb_close(self):
        self.tlb.CloseDevices()

    def tlb_query(self, msg):
        self._buff.Clear()
        self.tlb.Query(self.device_id, msg, self._buff)
        return self._buff.ToString()

    def set_remote_control(self):
        """ set laser to be controlled remotely """

        self.tlb_query('SYSTem:MCONtrol REM')

    def is_laser_on(self):
        """ Checks if the laser is on or off

        :return: (bool) whether or not emission is on or off
        """

        result = self.tlb_query('OUTPut:STATe?')
        status = bool(int(result))

        return status

    def turn_on(self):
        """ Turns on the laser """

        check_passed = self.check_operation_status()

        if check_passed:
            # Check if laser is on already
            if self.is_laser_on():
                self.log.info(f'Velocity laser is already on')
            else:
                self.tlb_query('OUTPut:STATe ON')
        else:
            self.log.error('cannot turn laser on!')

    def turn_off(self):
        """ Turns off the laser """

        check_passed = self.check_operation_status()

        if check_passed:
            # Check if laser is on already
            if self.is_laser_on():
                self.tlb_query('OUTPut:STATe OFF')
            else:
                self.log.info(f'Velocity laser is already off')
        else:
            self.log.error('cannot turn laser off!')

    def set_current(self, current):
        """ Set diode current setpoint in mA """

        self.tlb_query(f'SOURce:CURRent:DIODe {current}')

    def set_power(self, power):
        """ Set diode power setpoint in mW """

        self.tlb_query(f'SOURce:POWer:DIODe {power}')

    def set_wavelength(self, wavelength):
        """ Set wavelength setpoint in nm """

        check_passed = self.check_operation_status()

        if check_passed:
            self.tlb_query(f'SOURce:WAVElength {wavelength}')
            self.tlb_query('OUTPut:TRACK 1')
        else:
            self.log.error('cannot set wavelength!')

    def set_piezo_voltage(self, V):

        if V >= 0 and V <= 100:
            self.tlb_query(f'SOURce:VOLTage:PIEZo {np.round(V,2)}')
        else:
            self.log.error(f'Piezo voltage {V} out of range! Must be between 0 and 100!')

    def get_wavelength(self):
        """ Get wavelength setpoint in nm """

        return self.tlb_query(f'SOURce:WAVElength?')

    def query_laser_id(self):
        """ Identification string query """
        output = self.tlb_query('*IDN?')
        self.log.info('Connected to Laser: ' + output)

    def check_operation_status(self):
        """
        checks if Operation complete status is 1 twice in a row.
        This prevents the drive from crashing from receiving too
        many commands in quick succession, which completely shuts
        down the USB connection (only salvagable with power cycling).
        """
        watch_dog = 0
        doubledouble = 0
        while (doubledouble == 0):
            single = bool(int(self.tlb_query('*OPC?')))
            time.sleep(1)
            if single:
                doubledouble = bool(int(self.tlb_query('*OPC?')))
                time.sleep(1)
            watch_dog += 1
            if watch_dog > 30: # if checking operation status takes more than 30 seconds, abort
                break

        if doubledouble:
            self.log.info('Operation check passed. Laser ready to receive command.')
        else:
            self.log.error('Operation check not passing. Aborting command...')

        return doubledouble
