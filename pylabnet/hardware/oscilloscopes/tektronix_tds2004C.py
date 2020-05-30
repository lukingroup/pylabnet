from pyvisa import VisaIOError, ResourceManager
import re
import numpy as np

from pylabnet.utils.logging.logger import LogHandler

# Available input channels
CHANNEL_LIST = np.array([f'CH{i}' for i in range(1,5)])

# Available trigger channels
TRIGGER_SOURCE_LIST = np.append(CHANNEL_LIST, ['EXT', 'EXT5', 'LINE'])

class Driver():

    def reset(self):
        """ Create factory reset"""
        self.device.write('FAC;WAIT')
        self.log.info("Reset to factory settings successfull.")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient
        """

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

    def get_trigger_source(self):
        """ Return Trigger source"""

        # Query trigger source.
        res = self.device.query('TRIG:MAI:EDGE:SOU?')

        # Tidy up response using regex
        trig_channel = re.compile(
             ':TRIGGER:MAIN:EDGE:SOURCE[ ]([^\\n]+)'
            ).match(res).group(1)

        return trig_channel

    def set_trigger_source(self, trigger_source):
        """ Set trigger source"""

        if trigger_source not in TRIGGER_SOURCE_LIST:
            self.log.error(
                f"'{trigger_source}' no found, available trigger sources are {TRIGGER_SOURCE_LIST}.'"
            )

        # Set trigger source
        self.device.write(f'TRIG:MAI:EDGE:SOU {trigger_source}')

    def set_timing_scale(self, scale):
        """ Set the time base

        This defines the available display window, as 10
        divisions are displayed.

        :scale: Time per division (in s)
        """
        self.device.write(":HORIZONTAL:MAIN:SCALE {:e}".format(scale))

    def get_timing_scale(self):
        """ Get time base in secs per division"""

        res = self.device.query(":HORIZONTAL:MAIN:SCALE?")

        timing_res = re.compile(
             ':HORIZONTAL:MAIN:SCALE[ ]([0-9\.\+Ee-]+)'
            ).match(res).group(1)

        return float(timing_res)

    def set_single_run_acq(self):
        """Set acquisition mode to single run"""

        self.device.write('acquire:stopafter sequence')

    def acquire_single_run(self):
        """ Run single acquisition"""

        self.device.write('acquire:state on')

    def read_out_trace(self, channel):
        """ Read out trace

        :channel: Channel to read out (must be in CHANNEL_LIST)

        Returns np.array of sample points (in unit of Voltage divisions) and
        corresponding array of times (in seconds).
        """

        # TODO: Check if trace is activated.

        if channel not in CHANNEL_LIST:
            self.log.error(f"The channel '{channel}' is not available, available channels are {CHANNEL_LIST}.")

        # Set trace we want to look at
        self.device.write(f'DATa:SOUrce {channel}')

        # Set encoding
        self.device.write('data:encdg ascii')

        # Read out trace
        res = self.device.query('curve?')

        # Tidy up curve
        raw_curve = res.replace(':CURVE', '').replace(' ', '').replace('\n', '')

        # Transform in numpy array
        curve = np.fromstring(raw_curve,  dtype=int, sep=',')

        # Reconstruct time axis
        timebase = self.get_timing_scale()
        num_samples = len(curve)

        ts = np.arange(num_samples) *  timebase / int(num_samples/10)

        #TODO Rad out voltage divs

        return curve, ts
