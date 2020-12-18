import numpy as np
from si_prefix import split, prefix
import socket
import time

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogHandler
import pyqtgraph as pg
from pylabnet.utils.helper_methods import generate_widgets, unpack_launcher, find_client, load_config, get_gui_widgets
from pylabnet.network.client_server import thorlabs_pm320e

# Time between power meter calls to prevent crashes
BUFFER = 5e-3

class Monitor:
    RANGE_LIST = [
        'AUTO', 'R1NW', 'R10NW', 'R100NW', 'R1UW', 'R10UW', 'R100UW', 'R1MW',
        'R10MW', 'R100MW', 'R1W', 'R10W', 'R100W', 'R1KW'
    ]

    def __init__(self, pm_client, gui='fiber_coupling', logger=None, calibration=None, name=None, port=None):
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_clients: (client, list of clients) clients of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        :calibration: (float) Calibration value for power meter.
        :name: (str) Humand-readable name of the power meter.
        """


        self.log = LogHandler(logger)
        self.gui =Window(
            gui_template=gui,
            host=socket.gethostbyname(socket.gethostname()),
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

        self._initialize_gui()

    def sync_settings(self):
        """ Pulls current settings from PM and sets them to GUI """

        # Configure wavelength
        self.wavelength = self.pm.get_wavelength(1)

        self.widgets['number_widget'][-1].setValue(
            self.wavelength
        )

        # Configure Range to be Auto
        self.pm.set_range(1, self.RANGE_LIST[0])
        self.pm.set_range(2, self.RANGE_LIST[0])
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

        range_index = self.widgets['combo_widget'][channel].currentIndex()

        if channel == 0:
            if self.ir_index != range_index:
                self.ir_index = range_index
                self.pm.set_range(1, self.RANGE_LIST[self.ir_index])
        elif channel == 1:
             if self.rr_index != range_index:
                self.rr_index = range_index
                self.pm.set_range(2, self.RANGE_LIST[self.rr_index])

    def update_settings(self, channel=0):
        """ Checks GUI for settings updates and implements

        :param channel: (int) channel of power meter to use
        """

        gui_wl = self.widgets['number_widget_4'].value()

        if self.wavelength[channel] != gui_wl:
            self.wavelength[channel] = gui_wl
            self.pm[channel].set_wavelength(1, self.wavelength[channel])
            self.pm[channel].set_wavelength(2, self.wavelength[channel])

        gui_ir = self.gui.get_item_index(f'ir_{channel}')
        if self.ir_index[channel] != gui_ir:
            self.ir_index[channel] = gui_ir
            self.pm[channel].set_range(2*channel+1, self.RANGE_LIST[self.ir_index[channel]])

        gui_rr = self.gui.get_item_index(f'rr_{channel}')
        if self.rr_index[channel] != gui_rr:
            self.rr_index[channel] = gui_rr
            self.pm[channel].set_range(2*channel+2, self.RANGE_LIST[self.rr_index[channel]])

    def run(self):
        # Continuously update data until paused
        self.running = True

        while self.running:
            time.sleep(BUFFER)
            self._update_output()
            self.gui.force_update()

    def _update_output(self):
            """ Runs the power monitor """

            # Check for/implement changes to settings
            #self.update_settings(0)

            # Get all current values
            try:
                p_in = self.pm.get_power(1)
                split_in = split(p_in)

            # Handle zero error
            except OverflowError:
                p_in = 0
                split_in = (0, 0)
            try:
                p_ref = self.pm.get_power(2)
                split_ref = split(p_ref)
            except OverflowError:
                p_ref = 0
                split_ref = (0, 0)
            try:
                efficiency = np.sqrt(p_ref/(p_in*self.calibration[0]))
            except ZeroDivisionError:
                efficiency = 0
            values = [p_in, p_ref, efficiency]

            # For the two power readings, reformat.
            # E.g., split(0.003) will return (3, -3)
            # And prefix(-3) will return 'm'
            formatted_values = [split_in[0], split_ref[0], efficiency]
            value_prefixes =  [prefix(split_val[1]) for split_val in [split_in, split_ref]]

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
        self.plotdata =[np.zeros(1000) for i in range(self.num_plots)]

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

    def __init__(self, client, config:dict=None):

        self.client = client
        self.config = config
        if isinstance(self.client, thorlabs_pm320e.Client):
            self.type = 'thorlabs_pm320e'
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

        if self.type == 'thorlabs_pm320e':
            return self.client.get_power(channel)
        else:
            index = self.channels[channel-1]
            return ((self.m[index]
                     * (self.client.get_ai_voltage(self.channels[channel-1])
                        -self.z[index]))
                    + self.b[index])

    def get_wavelength(self, channel):
        if self.type == 'thorlabs_pm320e':
            return self.client.get_wavelength(channel)
        else:
            return 737

    def get_range(self, channel):
        if self.type == 'thorlabs_pm320e':
            return self.client.get_range(channel)
        else:
            return 'AUTO'

    def set_wavelength(self, channel, wavelength):
        if self.type == 'thorlabs_pm320e':
            return self.client.set_wavelength(channel, wavelength)
        else:
            return

    def set_range(self, channel, p_range):
        if self.type == 'thorlabs_pm320e':
            return self.client.set_range(channel, p_range)
        else:
            return


def launch(**kwargs):
    """ Launches the full fiber controll + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, _, params = unpack_launcher(**kwargs)

    # Unpack settings
    settings = load_config(
        kwargs['config'],
        logger=logger
    )

    try:
        pm_client = clients[('nidaqmx', settings['power_sensor']['device_id'])]
    except KeyError:
        logger.warn('Could not find nidaqmx AI for power detection by device ID')
        logger.info(f'Client dictionary: {clients}')
        pm_client = find_client(logger, clients, 'thorlabs_pm320e_front')

    calibration = [settings['calibration']]
    name = settings['name']
    pm = PMInterface(pm_client, settings)

    # Instantiate controller
    control = Monitor(
        pm_client=pm,
        logger=logger,
        calibration=calibration,
        name=name,
        port=logport
    )

    time.sleep(2)
    control.sync_settings()


    control.run()

    # Mitigate warnings about unused variables
    if loghost and logport and params:
        pass
