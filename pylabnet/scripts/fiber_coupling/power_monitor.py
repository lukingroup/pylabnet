import numpy as np
from si_prefix import split, prefix
import time

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.helper_methods import generate_widgets, unpack_launcher

class Monitor:
    CALIBRATION = [1e-4]
    RANGE_LIST = [
        'AUTO', 'R1NW', 'R10NW', 'R100NW', 'R1UW', 'R10UW', 'R100UW', 'R1MW',
        'R10MW', 'R100MW', 'R1W', 'R10W', 'R100W', 'R1KW'
    ]

    def __init__(self, pm_clients, gui_client, logger=None): 
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_clients: (client, list of clients) clients of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)
        self.wavelength = []
        self.ir_index, self.rr_index = [], []
        if isinstance(pm_clients, list):
            self.pm = pm_clients
        else:
            self.pm = [pm_clients]

        self.running = False
        self._initialize_gui()

    def sync_settings(self):
        """ Pulls current settings from PM and sets them to GUI """

        for channel, pm in enumerate(self.pm):

            # Configure wavelength
            self.wavelength.append(pm.get_wavelength(1))
            try:
                pm.set_wavelength(2, self.wavelength[channel])
            except:
                self.log.warn('Failed to set the wavelength to channel 2')
            self.gui.activate_scalar(scalar_label=f'wavelength_{channel}')
            self.gui.set_scalar(
                value=self.wavelength[channel],
                scalar_label=f'wavelength_{channel}'
            )
            self.gui.deactivate_scalar(scalar_label=f'wavelength_{channel}')

            # Configure Range
            self.ir_index.append(self.RANGE_LIST.index(pm.get_range(1).strip()))
            self.rr_index.append(self.RANGE_LIST.index(pm.get_range(2).strip()))
            self.gui.set_item_index(f'ir_{channel}', self.ir_index[channel])
            self.gui.set_item_index(f'rr_{channel}', self.rr_index[channel])

    def update_settings(self, channel=0):
        """ Checks GUI for settings updates and implements

        :param channel: (int) channel of power meter to use
        """

        gui_wl = self.gui.get_scalar(f'wavelength_{channel}')
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
        """ Runs the power monitor """

        self.running = True

        for channel, pm in enumerate(self.pm):
        
            # Check for/implement changes to settings
            self.update_settings(channel)
            
            # Get all current values
            p_in = pm.get_power(1)
            p_ref = pm.get_power(2)
            efficiency = np.sqrt(p_ref/(p_in*self.CALIBRATION[channel]))
            values = [p_in, p_ref, efficiency]

            # For the two power readings, reformat.
            # E.g., split(0.003) will return (3, -3)
            # And prefix(-3) will return 'm'
            split_in, split_ref = split(p_in), split(p_ref)
            formatted_values = [split_in[0], split_ref[0], efficiency]
            value_prefixes =  [prefix(split_val[1]) for split_val in [split_in, split_ref]]

            plot_label_list = [
                f'Input {channel+1}',
                f'Reflection {channel+1}',
                f'Coupling Efficiency {channel+1}'
            ]
            number_label_list = [
                f'input_power_{channel}',
                f'reflection_power_{channel}',
                f'coupling_{channel}'
            ]

            # Update GUI
            for plot_no, plot in enumerate(plot_label_list):
                self.gui.set_scalar(formatted_values[plot_no], number_label_list[plot_no])
                self.plots[channel][plot_no] = np.append(self.plots[channel][plot_no][1:], values[plot_no])
                self.gui.set_curve_data(
                    data=self.plots[channel][plot_no],
                    plot_label=plot,
                    curve_label=plot,
                )
                if plot_no < 2:
                    self.gui.set_label(text=f'{value_prefixes[plot_no]}W', label_label=self.labels[plot_no])

        self.running = False

    def _initialize_gui(self):
        """ Instantiates GUI by assigning widgets """

        self.graphs, self.legends, self.numbers, self.labels, self.combos = generate_widgets(
            dict(graph_widget=3, legend_widget=3, number_widget=4, label_widget=2, combo_widget=2)
        )
        self.plots = []

        for channel in range(len(self.pm)):

            # Graphs
            channel_plots = []
            plot_label_list = [
                f'Input {channel+1}',
                f'Reflection {channel+1}',
                f'Coupling Efficiency {channel+1}'
            ]
            for index, label in enumerate(plot_label_list):
                self.gui.assign_plot(
                    plot_widget=self.graphs[index],
                    plot_label=label,
                    legend_widget=self.legends[index]
                )
                self.gui.assign_curve(
                    plot_label=label,
                    curve_label=label
                )
                channel_plots.append(np.zeros(1000))
            self.plots.append(channel_plots)

            # Numbers
            number_label_list = [
                f'input_power_{channel}',
                f'reflection_power_{channel}',
                f'coupling_{channel}'
            ]
            for index, label in enumerate(number_label_list):
                self.gui.assign_scalar(
                    scalar_widget=self.numbers[index],
                    scalar_label=label
                )
                last_index = index

            self.gui.assign_scalar(
                scalar_widget=self.numbers[last_index+1],
                scalar_label=f'wavelength_{channel}'
            )

            # Assign prefix labels
            for label in self.labels:
                self.gui.assign_label(
                    label_widget=label,
                    label_label=label
                )

            self.gui.assign_container(
                container_widget=self.combos[0], 
                container_label=f'ir_{channel}'
            )
            self.gui.assign_container(
                container_widget=self.combos[1],
                container_label=f'rr_{channel}'
            )
            

def launch(**kwargs):
    """ Launches the full fiber controll + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    pm_client = clients['thorlabs_pm320e']
    gui_client = guis['fiber_coupling']

    # Instantiate controller
    control = Monitor(
        pm_clients=[pm_client],
        gui_client=gui_client,
        logger=logger
    )

    time.sleep(2)
    control.sync_settings()
    while True:

        if not control.gui.is_paused:
            control.run()

    # Mitigate warnings about unused variables
    if loghost and logport and params:
        pass
