from pyvisa import VisaIOError, ResourceManager

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
import numpy as np
import matplotlib.pyplot as plt
import pickle
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
            self.log.error(
                f'Invalid attenuation ({db}dB). Attenuation must be between 0dB and 75dB'
            )
        self.device.write(f'POW:ATT {int(db)}dB')
        self.log.info(f'Input attenuation set to {db}dB.')

    def set_center_frequency(self, center_frequency):
        ''' Set center frequency of trace.

        :center_frequency: Frequency in Hz (from 0 to 13.3 GHz)
        '''
        if not 0 <= center_frequency <= 13.2*1e9:
            self.log.error(
                f'Invalid center frequency ({center_frequency} Hz). Must be within 0 and 13.2 GHz'
            )

        self.device.write(f':SENSe:FREQuency:CENTer {center_frequency}')
        self.log.info(f'Center frequency set to {center_frequency} Hz')

    def set_frequency_span(self, frequency_span):
        ''' Set frequency span of trace.

        :frequency_span: Frequency span in Hz (from 0 to 13.3 GHz)
        '''
        if not 0 <= frequency_span <= 13.2*1e9:
            self.log.error(
                f'Invalid frequency span ({frequency_span} Hz). Must be within 0 and 13.2 GHz'
            )

        self.device.write(f':SENSe:FREQuency:SPAN {frequency_span}')
        self.log.info(f'Frequency span set {frequency_span} Hz')

    def toggle_cont(self, target_state):
        '''Switch between single shot and continuous acquisition mode

        :target_state: Index of targe stat. 1 for continuous mode, 0 for single shot mode.
        '''
        self.device.write(f'INIT:CONT {target_state}')

    def get_frequency_array(self):
        '''Constructs array of frequencies associated with trace points'''

        # Sweep start frequency.
        start_freq = float(self.device.query(':SENSe:FREQuency:STARt?'))

        # Sweep end frequency.
        end_freq = float(self.device.query(':SENSe:FREQuency:STOP?'))

        # Number of sweep points.
        num_sweep_points = float(self.device.query('SENSE:SWEEP:POINTS?'))

        # Array containing frequencies of each sweep point.
        frequencies = np.linspace(start_freq, end_freq, num_sweep_points)

        return frequencies

    def read_trace(self):
        ''' Read and return trace

        Retruns array trace contaning frequencies (in Hz) of data points in
        trace[:,0] and power levels (in dBm) in trace[:,1]
        '''

        # Set to single shot mode.
        self.toggle_cont(0)

        # Trigger a sweep and wait for sweep to complete.
        self.device.write('INIT:IMM;*WAI')

        # Specify units in dBm.
        self.device.write('UNIT:POW DBM')

        # Specify data format as ASCII.
        self.device.write('FORM:DATA ASC')

        # Trigger a sweep and wait for sweep to complete.
        self.device.write('INIT:IMM;*WAI')

        # Query trace data
        dbm_measurement = self.device.query_ascii_values('TRAC:DATA? TRACE1')

        # Return to continuos monitoring mode
        self.toggle_cont(1)

        # Read frequency axis
        frequencies = self.get_frequency_array()

        # Combine trace data
        trace = np.stack((frequencies, dbm_measurement), axis=-1)

        return trace


class E4405BService(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_display_off(self):
        return self._module.display_off()

    def exposed_display_on(self):
        return self._module.display_on()

    def exposed_set_attenuation(self, db):
        return self._module.set_attenuation(db)

    def exposed_set_center_frequency(self, center_frequency):
        return self._module.set_center_frequency(center_frequency)

    def exposed_set_frequency_span(self, frequency_span):
        return self._module.set_frequency_span(frequency_span)

    def exposed_read_trace(self):
        trace = self._module.read_trace()
        return pickle.dumps(trace)

    def exposed_query(self, command):
        query = self._module.device.query(command)
        return pickle.dumps(query)

    def exposed_write(self, command):
        return self._module.device.write(command)


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

    def read_trace(self):
        pickled_trace = self._service.exposed_read_trace()
        return pickle.loads(pickled_trace)

    def write(self, command):
        return self._service.exposed_write(command)

    def query(self, command):
        pickled_query = self._service.exposed_query(command)
        return pickle.loads(pickled_query)

    def plot_trace(self):
        '''Reads and plots trace'''

        trace = self.read_trace()

        # Plot trace
        plt.figure()
        plt.plot(trace[:, 0]/1e9, trace[:, 1])
        plt.xlabel('Frequency [GHz]')
        plt.ylabel('Power [dBm]')
        plt.show()


class E4405BMarker():
    ''' Class handling assignment and read out of peak markers.'''

    def __init__(self, e4405Bclient, name, marker_num):
        ''' Initialized the marker

        :e4405Bclient: Instance of E4405BClient.
        :name: A human readable name of the marker.
        :marker_num: Marker number from 1 to 4.
        '''
        self.client = e4405Bclient
        self.marker_num = marker_num
        self.name = name

        # Set marker as position marker (floating, unassigned to a peak).
        self.set_as_position()

    def set_as_position(self):
        '''Specify marker type as position marker (standard).'''
        self.client.write(f':CALCulate:MARKer{self.marker_num}:MODE POSition;*WAI')

    def set_to_maximum(self):
        '''Set marker to maximum peak value of trace.'''
        self.client.write(f':CALCulate:MARKer{self.marker_num}:MAXimum;*WAI')

    def _toggle_freq_count(self, state):
        '''Change frequency count setting

        :state (int): 1 to toggle frequency counting on, 0 to toggle it off.
        '''
        self.client.write(f':CALCulate:MARKer{self.marker_num}:FCOunt:STATe {state};*WAI')

    def _get_freq(self):
        ''' Read out frequency

        Note: Work only if _toggle_freq_count was called, outputs 9e15 if count state is off.
        '''
        return float(self.client.query(f':CALCulate:MARKer{self.marker_num}:FCOunt:X?;*WAI'))

    def get_power(self):
        '''Reads out power of marker position (in dbm)'''
        return float(self.client.query(f':CALCulate:MARKer{self.marker_num}:Y?;*WAI'))

    def look_left(self):
        '''Focus marker on next peak left.'''
        self.client.write(f':CALCulate:MARKer{self.marker_num}:MAXimum:LEFT;*WAI')
        time.sleep(0.1)

    def look_right(self):
        '''Focus marker on next peak right.'''
        self.client.write(f':CALCulate:MARKer{self.marker_num}:MAXimum:RIGHT;*WAI')
        time.sleep(0.1)

    def read_freq(self):
        ''' Read out frequency of maker.

        This is done by first enabling count state, reading out the frequency
        and disabling the count state. For some reason, very long sleep times
        between commands are necessary to ensure correct readout of the frequency.
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
