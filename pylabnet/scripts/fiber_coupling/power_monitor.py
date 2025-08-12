import numpy as np
from si_prefix import split, prefix
import time

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogHandler
import pyqtgraph as pg
from pylabnet.utils.helper_methods import generate_widgets, unpack_launcher, find_client, load_config, get_gui_widgets, load_script_config, get_ip
from pylabnet.network.client_server import thorlabs_pm320e, newport_2936

# Time between power meter calls to prevent crashes
BUFFER = 5e-3

THORLABS_RANGE_COMMAND_LIST = [
    'AUTO', 'R1NW', 'R10NW', 'R100NW', 'R1UW', 'R10UW', 'R100UW',
    'R1MW', 'R10MW', 'R100MW', 'R1W', 'R10W', 'R100W', 'R1KW'
]
THORLABS_RANGE_DISPLAY_LIST = [
    "Auto", "1 nW", "10 nW", "100 nW", "1 uW", "10 uW", "100 uW",
    "1 mW", "10 mW", "100 mW", "1 W", "10 W", "100 W", "1 kW"
]

NEWPORT_RANGE_COMMAND_LIST = ["AUTO", 0, 1, 2, 3, 4, 5, 6, 7]
NEWPORT_RANGE_DISPLAY_LIST = [
    "Auto", "281 nW", "2.81 uW", "28.1 uW", "281 uW", "2.81 mW",
    "28.1 mW", "281 mW", "2.81 W"
]


class Monitor:

    def __init__(self, pm_client, gui='fiber_coupling', logger=None, calibration=None, name=None, port=None):
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_clients: (client, list of clients) clients of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        :calibration: (float) Calibration value for power meter.
        :name: (str) Human-readable name of the power meter.
        """

        self.log = LogHandler(logger)
        self.gui = Window(
            gui_template=gui,
            host=get_ip(),
            port=port
        )

        self.gui.apply_stylesheet()
        self.wavelength = []
        self.calibration = calibration
        self.name = name
        self.ir_index, self.rr_index = [], []
        self.pm = pm_client
        self.running = False
        self.num_plots = 3

        # Get all GUI widgets
        self.widgets = get_gui_widgets(
            self.gui,
            graph_widget=self.num_plots,
            number_widget=4,
            label_widget=2,
            name_label=1,
            combo_widget=2
        )

        # Dynamically populate the power ranges
        if self.pm.type == "thorlabs_pm320e":
            self.power_dropdown_list, self.power_command_list = THORLABS_RANGE_DISPLAY_LIST, THORLABS_RANGE_COMMAND_LIST
        elif self.pm.type == "newport_2936":
            self.power_dropdown_list, self.power_command_list = NEWPORT_RANGE_DISPLAY_LIST, NEWPORT_RANGE_COMMAND_LIST
        else:
            self.power_dropdown_list, self.power_command_list = ["Auto"], ["Auto"]

        for power_str in self.power_dropdown_list:
            self.widgets['combo_widget'][0].addItem(power_str)
            self.widgets['combo_widget'][1].addItem(power_str)

        self._initialize_gui()

    def sync_settings(self):
        """ Pulls current settings from PM and sets them to GUI """

        # Configure wavelength
        self.wavelength = self.pm.get_wavelength(1)

        self.widgets['number_widget'][-1].setValue(
            self.wavelength
        )

        # Configure Range to be Auto
        self.pm.set_auto(1)
        self.pm.set_auto(2)

        self.ir_index = 0
        self.rr_index = 0

        # Connect wavelength change action.
        self.widgets['number_widget'][-1].valueChanged.connect(self._update_wavelength)

        # Connect range change.
        self.widgets['combo_widget'][0].currentIndexChanged.connect(lambda: self._update_range(0))
        self.widgets['combo_widget'][1].currentIndexChanged.connect(lambda: self._update_range(1))

    def _update_wavelength(self):
        """ Updates wavelength of pm to WL of GUI"""

        gui_wl = self.widgets['number_widget'][-1].value()

        if self.wavelength != gui_wl:
            self.wavelength = gui_wl
            self.pm.set_wavelength(1, self.wavelength)
            self.pm.set_wavelength(2, self.wavelength)

    def _update_range(self, channel):
        """ Update range settings if combobox has been changed."""

        # Current index of range dropdown box
        range_index = self.widgets['combo_widget'][channel].currentIndex()

        # Previous range index is ir_index or rr_index depending on which channel was changed
        # Channel is 0-indexed (0 or 1)
        if channel == 0:
            if self.ir_index != range_index:
                self.ir_index = range_index
                self.pm.set_range(1, self.power_command_list[self.ir_index])
        elif channel == 1:
            if self.rr_index != range_index:
                self.rr_index = range_index
                self.pm.set_range(2, self.power_command_list[self.rr_index])

    def run(self):
        # Continuously update data until paused
        self.running = True

        while self.running:
            time.sleep(BUFFER)
            self._update_output()
            self.gui.force_update()

    def _update_output(self):
        """ Runs the power monitor """

        # Get all current values
        try:
            p_in = self.pm.get_power(1)
            split_in = split(p_in)
            if p_in > 1E20:
                raise OverflowError
        # Handle zero error
        except OverflowError:
            p_in = 0
            split_in = (0, 0)
        try:
            p_ref = self.pm.get_power(2)
            split_ref = split(p_ref)
            if p_ref > 1E20:
                raise OverflowError
        except OverflowError:
            p_ref = 0
            split_ref = (0, 0)
        try:
            efficiency = np.sqrt(p_ref / (p_in * self.calibration[0]))
            # Clip to max 1 efficiency if it's a valid number
            if not np.isnan(efficiency):
                efficiency = min(1, efficiency)
        except ZeroDivisionError:
            efficiency = 0
        values = [p_in, p_ref, efficiency]

        # For the two power readings, reformat.
        # E.g., split(0.003) will return (3, -3) and prefix(-3) will return 'm'
        formatted_values = [split_in[0], split_ref[0], efficiency]
        value_prefixes = [prefix(split_val[1]) for split_val in [split_in, split_ref]]

        # Update GUI
        for plot_no in range(self.num_plots):
            # Update Number
            self.widgets['number_widget'][plot_no].setValue(formatted_values[plot_no])

            # Update Curve
            self.plotdata[plot_no] = np.append(self.plotdata[plot_no][1:], values[plot_no])
            self.widgets[f'curve_{plot_no}'].setData(self.plotdata[plot_no])

            if plot_no < 2:
                self.widgets["label_widget"][plot_no].setText(f'{value_prefixes[plot_no]}W')

    def _initialize_gui(self):
        """ Instantiates GUI by assigning widgets """

        # Store plot data
        self.plotdata = [np.zeros(1000) for i in range(self.num_plots)]

        for plot_no in range(self.num_plots):
           # Create a curve and store the widget in our dictionary
            self.widgets[f'curve_{plot_no}'] = self.widgets['graph_widget'][plot_no].plot(
                pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
            )


class PMInterface:
    """
    Interface class to allow other modules to be called in same
    way as a Thorlabs power meter

    Currently supports NI AI with power calibration curve via config
    power (uW) = m*(x-z) + b
    """

    def __init__(self, client, config: dict = None):

        self.client = client
        self.config = config
        if isinstance(self.client, thorlabs_pm320e.Client):
            self.type = 'thorlabs_pm320e'
        elif isinstance(self.client, newport_2936.Client):
            self.type = 'newport_2936'
            self.input_bg = self.config['input_bg']
            self.ref_bg = self.config['reflection_bg']
        else:
            self.type = 'nidaqmx'
            self.channels = [
                self.config['input']['channel'],
                self.config['reflection']['channel']
            ]
            self.m = [
                self.config['input']['m'],
                self.config['reflection']['m']
            ]
            self.b = [
                self.config['input']['b'],
                self.config['reflection']['b']
            ]
            self.z = [
                self.config['input']['z'],
                self.config['reflection']['z']
            ]

    def get_power(self, channel):
        # Thorlabs and Newport are 1-indexed
        if self.type == 'thorlabs_pm320e':
            return self.client.get_power(channel)
        # Newport has an extra calibration for background power reading with no light
        elif self.type == 'newport_2936':
            power_reading = self.client.get_power(channel)
            if channel == 1: # Input
                return power_reading - self.input_bg
            elif channel == 2: # Reflection
                return power_reading - self.ref_bg
            else: # Should not occur
                return power_reading

        # DAQ is 0-indexed
        else:
            index = channel - 1
            return ((self.m[index]
                     * (self.client.get_ai_voltage(self.channels[index])[0]
                        - self.z[index]))
                    + self.b[index]) * 1e-6

    def get_wavelength(self, channel):
        if self.type in ['thorlabs_pm320e', 'newport_2936']:
            return self.client.get_wavelength(channel)
        else:
            return 737

    def get_range(self, channel):
        if self.type in ['thorlabs_pm320e', 'newport_2936']:
            return self.client.get_range(channel)
        else:
            return 'AUTO'

    def set_wavelength(self, channel, wavelength):
        if self.type in ['thorlabs_pm320e', 'newport_2936']:
            return self.client.set_wavelength(channel, wavelength)
        else:
            return

    def set_range(self, channel, p_range):
        if self.type == 'thorlabs_pm320e':
            return self.client.set_range(channel, p_range)
        elif self.type == 'newport_2936':
            if p_range == "AUTO":
                self.set_auto(channel)
            else:
                # Newport's Auto mode will take precedence if still active
                self.client.set_auto(channel, False)
                return self.client.set_range(channel, p_range)
        else:
            return

    def set_auto(self, channel):
        if self.type == 'thorlabs_pm320e':
            return self.client.set_range(channel, "AUTO")
        elif self.type == 'newport_2936':
            return self.client.set_auto(channel, True)
        else:
            return


def launch(**kwargs):
    """ Launches the full fiber controll + GUI script """

    # Unpack and assign parameters
    logger = kwargs['logger']
    clients = kwargs['clients']
    logport = kwargs['logport']

    # Unpack settings
    settings = load_script_config(
        'power_monitor',
        kwargs['config'],
        logger=logger
    )

    # Find the client
    device_config = None
    for server in settings['servers']:
        if 'name' in server and server['name'] == 'power_sensor':
            device_type = server['type']
            device_config = server['config']
            break
    try:
        pm_client = find_client(clients, settings, device_type, device_config, logger)
    except NameError:
        logger.error('No power_sensor device identified in script config file')

    logger.info(f'Found PM client {pm_client}')
    calibration = [settings['calibration']]
    name = settings['name']
    pm = PMInterface(pm_client, settings)

    # Instantiate controller
    control = Monitor(
        pm_client=pm,
        logger=logger,
        calibration=calibration,
        name=name,
        port=kwargs['server_port']
    )

    time.sleep(2)
    control.sync_settings()

    control.run()
