from pyvisa import VisaIOError, ResourceManager
import re
import numpy as np

from pylabnet.utils.logging.logger import LogHandler

# Available input channels.
CHANNEL_LIST = np.array([f'CH{i}' for i in range(1, 5)])

# Available trigger channels.
TRIGGER_SOURCE_LIST = np.append(CHANNEL_LIST, ['EXT', 'EXT5', 'LINE'])

# Available signal attenuation settings.
ATTENUATIONS = [1, 10, 20, 50, 100, 200, 500, 1000]


class Driver():

    def reset(self):
        """ Create factory reset"""
        self.device.write('FAC;WAIT')
        self.log.info("Reset to factory settings successfull.")

    def __init__(self, gpib_address, logger):
        """Instantiate driver class.

        :gpib_address: GPIB-address of the scope, e.g. 'GPIB0::12::INSTR'
            Can be read out by using
                rm = pyvisa.ResourceManager()
                rm.list_resources()
        :logger: And instance of a LogClient.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            device_id = self.device.query('*IDN?')
            self.log.info(f"Successfully connected to {device_id}.")
        except VisaIOError:
            self.log.error(f"Connection to {gpib_address} failed.")

        # We set a more forgiving timeout of 10s (default: 2s).
        self.device.timeout = 10000

        # Reset to factory settings.
        self.reset()

        # Set all attenuations to 1x.
        for channel in CHANNEL_LIST:
            self.set_channel_attenuation(channel, 1)

    def get_trigger_source(self):
        """ Return Trigger source."""

        # Query trigger source.
        res = self.device.query('TRIG:MAI:EDGE:SOU?')

        # Tidy up response using regex.
        trig_channel = re.compile(
                    ':TRIG:MAI:EDGE:SOU[ ]([^\\n]+)'
                ).match(res).group(1)

        return trig_channel

    def set_trigger_source(self, trigger_source):
        """ Set trigger source."""

        if trigger_source not in TRIGGER_SOURCE_LIST:
            self.log.error(
                f"'{trigger_source}' no found, available trigger sources are {TRIGGER_SOURCE_LIST}.'"
            )

        # Set trigger source.
        self.device.write(f'TRIG:MAI:EDGE:SOU {trigger_source}')

    def set_timing_scale(self, scale):
        """ Set the time base.

        This defines the available display window, as 10
        divisions are displayed.

        :scale: Time per division (in s)
        """
        self.device.write(":HORIZONTAL:MAIN:SCALE {:e}".format(scale))

    def extract_params(self, command, value):
        """ Uses regex to extract float values from return values.

        :command: The command used to query, without the final '?'
        :value: The return value of a query.
        """

        value = float(re.compile(
            f'{command} ([0-9\.\+Ee-]+)'
        ).match(value).group(1))

        return value

    def get_timing_scale(self):
        """ Get time base in secs per division."""

        command = ":HOR:MAI:SCA"
        timing_res = self.device.query(f"{command}?")

        timing_res = self.extract_params(command, timing_res)

        return timing_res

    def set_single_run_acq(self):
        """Set acquisition mode to single run."""

        self.device.write('acquire:stopafter sequence')

    def acquire_single_run(self):
        """ Run single acquisition."""

        self.device.write('acquire:state on')

    def _check_channel(self, channel):
        """ CHeck if channel is in CHANNEL list."""

        if channel not in CHANNEL_LIST:
            self.log.error(
                f"The channel '{channel}' is not available, available channels are {CHANNEL_LIST}."
            )

    def unitize_trace(self, trace, trace_preamble):
        """Transform unitless trace to trace with units, constructs time array.

        :trace: (np.array) Unitless array as provided by oscilloscope.
        :trace_preamble: (string) Waveform preamble.

        Returns trace, a np.array in correct units, ts, the time
        array in seconds, and y_unit, the unit of the Y-axis.
        """

        # Overcharged regex extracting all relevant paramters.
        wave_pre_regex = 'NR_P (?P<n_points>[0-9\.\+Ee-]+).+PT_F (?P<pf_f>[^"]+).+XUN "(?P<x_unit>[^"]+).+XIN (?P<x_incr>[0-9\\.\\+Ee-]+).+XZE (?P<x_zero>[0-9\\.\\+Ee-]+).+PT_O (?P<pt_off>[0-9\\.\\+Ee-]+).+YUN "(?P<y_unit>[^"]+).+YMU (?P<y_mult>[0-9\\.\\+Ee-]+).+YOF (?P<y_off>[0-9\\.\\+Ee-]+).+YZE (?P<y_zero>[0-9\\.\\+Ee-]+)'

        wave_pre_matches = re.search(wave_pre_regex, trace_preamble)

        # Adjust trace as shown in the coding manual 2-255.
        trace = (
            trace - float(wave_pre_matches['y_off'])
        ) * \
            float(wave_pre_matches['y_mult']) + \
            float(wave_pre_matches['y_zero'])

        # Construct timing array as shown in the coding manual 2-250.
        ts = float(wave_pre_matches['x_zero']) + \
            (
                np.arange(int(wave_pre_matches['n_points'])) -
                int(wave_pre_matches['pt_off'])
        ) * float(wave_pre_matches['x_incr'])

        x_unit = wave_pre_matches['x_unit']
        y_unit = wave_pre_matches['y_unit']

        # Construct trace dictionary.
        trace_dict = {
            'trace': trace,
            'ts': ts,
            'x_unit': x_unit,
            'y_unit': y_unit
        }

        return trace_dict

    def read_out_trace(self, channel, curve_res=1):
        """ Read out trace

        :channel: Channel to read out (must be in CHANNEL_LIST).
        :curve_res: Bit resolution for returned data. If 1, value range is from -127 to 127,
            if 2, the value range is from -32768 to 32768.

        Returns np.array of sample points (in unit of Voltage divisions) and
        corresponding array of times (in seconds).
        """

        self._check_channel(channel)

        # Enable trace.
        self.show_trace(channel)

        # Run acquisition.
        self.acquire_single_run()

        if curve_res not in [1, 2]:
            self.log.error("The bit resolution of the curve data must be either 1 or 2.")

        # Set curve data to desired bit.
        self.device.write(f'DATa:WIDth {curve_res}')

        # Set trace we want to look at.
        self.device.write(f'DATa:SOUrce {channel}')

        # Set encoding.
        self.device.write('data:encdg ascii')

        # Read out trace.
        res = self.device.query('curve?')

        # Tidy up curve.
        raw_curve = res.replace(':CURV', '').replace(' ', '').replace('\n', '')

        # Transform in numpy array.
        trace = np.fromstring(raw_curve, dtype=int, sep=',')

        # Read wave preamble.
        wave_pre = self.device.query('WFMPre?')

        # Transform units of trace.
        trace_dict = self.unitize_trace(trace, wave_pre)

        return trace_dict

    def show_trace(self, channel):
        """Display trace.

        Required for trace readout.
        """

        self._check_channel(channel)

        self.device.write(f'SELect:{channel} 1')

    def hide_trace(self, channel):
        """Hide trace."""

        self._check_channel(channel)

        self.device.write(f'SELect:{channel} 0')

    def _check_channel_attenuation(self, attenuation):
        """Check if attenuation is within option set."""

        if attenuation not in ATTENUATIONS:
            self.log.error(
                f"The attenuation '{attenuation}x' is not available, available attenuations are {ATTENUATIONS}."
            )

    def get_channel_attenuation(self, channel):
        """Get the attenuation of the channel.

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        """

        # Check if channel and attenuation is valid.
        self._check_channel(channel)

        # Get attenuation.
        command = f":{channel}:PRO:GAIN"
        attenuation = self.device.query(f"{command}?")

        # Extract float.
        attenuation = self.extract_params(command, attenuation)

        return attenuation

    def set_channel_attenuation(self, channel, attenuation):
        """Set the attenuation of the channel.

        This setting will scale the y-axis unit accordingly

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        :attenuation: (int) Attenuation, possible values see ATTENUATIONS.
        """

        # Check if channel and attenuation is valid.
        self._check_channel(channel)
        self._check_channel_attenuation(attenuation)

        # Set attenuation.
        self.device.write(f'{channel}:PRO:GAIN {attenuation}')

    def get_channel_scale(self, channel):
        """ Return vertical scale of channel.

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        """

        self._check_channel(channel)
        command = f":{channel}:SCA"
        scale = self.device.query(f"{command}?")

        # Extract float.
        scale = self.extract_params(command, scale)

        return scale

    def set_channel_scale(self, channel, range):
        """ Return vertical scale of channel.

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        :range: (float) Vertical range, in Volt/vertical division.
            Corresponds to 'Scale' turning knob.
            Must be between 5 mv/div and 5 V/div.
        """

        self._check_channel(channel)

        if not (5e-3 <= range <= 5):
            self.log.error('Range must be between 5 mv/div and 5 V/div.')

        # Set scale.
        self.device.write(f'{channel}:SCAle {range}')

    def get_channel_pos(self, channel):
        """Get vertical position of channel trace.

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        """

        self._check_channel(channel)

        command = f":{channel}:POS"
        pos = self.device.query(f"{command}?")

        # Extract float.
        pos = self.extract_params(command, pos)

        return pos

    def set_channel_pos(self, channel, pos):
        """Set vertical position of channel trace.

        :channel: (str) Channel, possible values see CHANNEL_LIST.
        :pos: (str) Vertical postion, in divs above center graticule.
            The maximum and minimum value of pos
            depends on the channel scale.
        """

        self._check_channel(channel)

        self.device.write(f'{channel}:POS {pos}')

    def get_horizontal_position(self):
        """Get the horizontal position of the traces.

        The return value in seconds is the difference between
        the trigger point ant the center graticule.
        """

        command = ":HOR:MAI:POS"
        hor_pos = self.device.query(f"{command}?")

        hor_pos = self.extract_params(command, hor_pos)

        return hor_pos

    def set_horizontal_position(self, hor_pos):
        """Set the horizontal position of the traces.

        The return value in seconds is the difference between
        the trigger point ant the center graticule.

        :hor_pos: (float) Horizontal position in s.
        """

        command = ":HOR:MAI:POS"
        self.device.write(f"{command} {hor_pos}")

    def trig_level_to_fifty(self):
        """Set main trigger level to 50%"""
        self.device.write('TRIGger:MAIn SETLEVel')

    def get_trigger_level(self):
        """Get trigger level."""

        trig_level = self.device.query(':TRIGGER:MAIN:LEVEL?')
        trig_level = self.extract_params('::TRIG:MAI:LEV', trig_level)

        return trig_level

    def set_trigger_level(self, trigger_level):
        """Set trigger level.

        :trigger_level: (float) Trigger level in Volts.
        """

        self.device.write(f':TRIGGER:MAIN:LEVEL {trigger_level}')
