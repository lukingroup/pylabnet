from pyvisa import VisaIOError, ResourceManager

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.mw_src import MWSrcInterface, MWSrcError
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class E4405BDriver():
    '''Driver class for GPIB controlled Agilent EE405 Spectrum analyser'''

    def __init__(self, gpib_address, logger):
        '''Instantiate driver class

        :gpib_address: GPIB-address of spectrum analyzer, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient
        '''

        # Instantiate log
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

    def display_off(self):
        ''' Power off display '''
        self.device.write(':DISPlay:ENABle OFF')

    def display_on(self):
        ''' Power on display '''
        self.device.write(':DISPlay:ENABle ON')

    def set_attenuation(self, db):
        ''' Set input attenuation
        :db: Target attenuation in dB, must be between 0 and 75
        '''

        if not 0 <= db <= 75:
            self.log.error(f'Invalid attenuation ({db}dB). Attenuation must be between 0dB and 75dB')
        self.device.write(f'POW:ATT {int(db)}dB')
