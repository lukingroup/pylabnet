import Newport
#from System.Text import StringBuilder


from pylabnet.utils.logging.logger import LogHandler


class Driver:
    """ Driver class for Toptica DLC Pro """

    def __init__(self, device_id, product_id=4106, logger=None):
        """ Instantiates DLC_Pro object

        :param host: (str) hostname of laser (IP address)
        :param port: (int) port number, toptica defaults to 1998
        :num_lasers: Number of installed lasers
        :param logger: (LogClient)
        """

        self.device_id = device_id
        self.product_id = product_id
        self.log = LogHandler(logger)
        self.tlb = None

        #self._buff = StringBuilder(64)

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
        # self._buff.Clear()
        # self.tlb.Query(self.device_id, msg, self._buff)
        # return self._buff.ToString()
        return self.tlb.Query(self.device_id, msg)

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

        # Check if laser is on already
        if self.is_laser_on():
            self.log.info(f'Velocity laser is already on')
        else:
            self.tlb_query('OUTPut:STATe ON')

    def turn_off(self):
        """ Turns off the laser """

        # Check if laser is on already
        if self.is_laser_on():
            self.tlb_query('OUTPut:STATe OFF')
        else:
            self.log.info(f'Velocity laser is already off')

    def set_current(self, current):
        """ Set diode current setpoint in mA """

        self.tlb_query(f'SOURce:CURRent:DIODe {current}')

    def set_power(self, power):
        """ Set diode power setpoint in mW """

        self.tlb_query(f'SOURce:POWer:DIODe {power}')

    def set_wavelength(self, wavelength):
        """ Set wavelength setpoint in nm """

        self.tlb_query(f'SOURce:WAVElength {wavelength}')
        self.tlb_query('OUTPut:TRACK 1')

    def query_laser_id(self):
        """ Identification string query """
        self.log.info('*IDN?')
