from pyvisa import VisaIOError, ResourceManager

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase
import time


class E4405BDriver():
    '''Driver class for GPIB controlled Agilent EE405 Spectrum analyser'''

    def reset(self):
        ''' Create factory reset'''
        self.device.write('*RST')
        self.log.info("Reset to factory settings successfull.")

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

        # reset to factory settings
        self.reset()

    def display_off(self):
        ''' Power off display '''
        self.device.write(':DISPlay:ENABle OFF')
        self.log.info("Display off.")

    def display_on(self):
        ''' Power on display '''
        self.device.write(':DISPlay:ENABle ON')
        self.log.info("Display on.")

    def set_attenuation(self, db):
        ''' Set input attenuation
        :db: Target attenuation in dB, must be between 0 and 75
        '''

        if not 0 <= db <= 75:
            self.log.error(f'Invalid attenuation ({db}dB). Attenuation must be between 0dB and 75dB')
        self.device.write(f'POW:ATT {int(db)}dB')
        self.log.info(f'Input attenuation set to {db}dB.')

    def set_center_frequency(self, center_frequency):
        ''' Set center frequency of trace.

        :center_frequency: Frequency in Hz (from 0 to 13.3 GHz)
        '''
        if not 0 <= center_frequency <= 13.2*1e9:
            self.log.error(f'Invalid center frequency ({center_frequency} Hz). Must be within 0 and 13.2 GHz')

        self.device.write(f':SENSe:FREQuency:CENTer {center_frequency}')
        self.log.info(f'Center frequency set to {center_frequency} Hz')

    def set_frequency_span(self, frequency_span):
        ''' Set frequency span of trace.

        :frequency_span: Frequency span in Hz (from 0 to 13.3 GHz)
        '''
        if not 0 <= frequency_span <= 13.2*1e9:
            self.log.error(f'Invalid frequency span ({frequency_span} Hz). Must be within 0 and 13.2 GHz')

        self.device.write(f':SENSe:FREQuency:SPAN {frequency_span}')
        self.log.info(f'Frequency span set {frequency_span} Hz')


class E4405BMarker():
    ''' Class handling assignment and read out of peak markers'''

    def __init__(self, e4405Bdevice, name, marker_num):
        ''' Initialized the marker

        :e4405Bdevice: Instance of E4405BDriver.
        :name: A human readable name of the marker.
        :marker_num: Marker number from 1 to 4.
        '''
        self.spectrum_analyzer = e4405Bdevice
        self.name = name
        self.marker_num = marker_num

        # Set marker as position marker
        self.set_as_position()

    def set_as_position(self):
        '''Specify marker type as position marker (standard).'''
        self.spectrum_analyzer.device.write(f':CALCulate:MARKer{self.marker_num}:MODE POSition')

    def set_to_maximum(self):
        '''Set marker to maximum peak value of trace.'''
        self.spectrum_analyzer.device.write(f':CALCulate:MARKer{self.marker_num}:MAXimum')

    def _toggle_freq_count(self, state):
        '''Change frequency count setting

        :state (int): 1 to toggle frequency counting on, 0 to toggle it off
        '''
        self.spectrum_analyzer.device.write(f':CALCulate:MARKer{self.marker_num}:FCOunt:STATe {state}')

    def _get_freq(self):
        ''' Read out frequency

        Note: Work only if _toggle_freq_count was called, outputs 9e15 if count state is off.
        '''
        return float(self.spectrum_analyzer.device.query(f':CALCulate:MARKer{self.marker_num}:FCOunt:X?'))

    def get_power(self):
        '''Reads out power of marker position (in dbm)'''
        return float(self.spectrum_analyzer.device.query(f':CALCulate:MARKer{self.marker_num}:Y?'))

    def look_left(self):
        '''Focus marker on next peak left.'''
        self.spectrum_analyzer.device.write(f':CALCulate:MARKer{self.marker_num}:MAXimum:LEFT')

    def look_right(self):
        '''Focus marker on next peak right.'''
        self.spectrum_analyzer.device.write(f':CALCulate:MARKer{self.marker_num}:MAXimum:RIGHT')

    def read_freq(self):
        ''' Read out frequency of maker.

        This is done by first enabling count state, reading out the frequency
        and disabling the count state.
        '''

        # Turn on frequency capture
        self._toggle_freq_count(1)

        time.sleep(1)

        # Read off frequency
        freq = self._get_freq()

        time.sleep(1)

        # Turn off frequency capture
        self._toggle_freq_count(0)

        return freq


class E4405BService(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_display_off(self):
        return self.display_off()

    def exposed_display_on(self):
        return self.display_on()

    def exposed_set_attenuation(self, db):
        return self._module.set_attenuation(db)

    def exposed_set_center_frequency(self, center_frequency):
        return self._module.set_center_frequency(center_frequency)

    def exposed_set_frequency_span(self, frequency_span):
        return self._module.set_frequency_span(frequency_span)


class E4405BClient(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def display_off(self):
        return self._service.exposed_display_off()

    def display_on(self):
        return self._service.exposed_display_on()

    def set_attenuation(self, db):
        return self._service.exposed_set_attenuation(db)

    def set_center_frequency(self, center_frequency):
        return self._service.exposed_set_center_frequency(center_frequency)

    def set_frequency_span(self, frequency_span):
        return self._service.exposed_set_frequency_span(frequency_span)