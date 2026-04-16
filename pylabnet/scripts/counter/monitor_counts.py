""" Generic script for monitoring counts from a counter """

import numpy as np
import time
import pyqtgraph as pg
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogClient
from pylabnet.scripts.pause_script import PauseService
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server import si_tt
from pylabnet.utils.helper_methods import load_script_config, get_ip, unpack_launcher, load_config, get_gui_widgets, get_legend_from_graphics_view, find_client, load_script_config

from pyqtgraph import PlotWidget, GraphicsView, GraphicsScene
from pyqtgraph.graphicsItems.LegendItem import LegendItem
from PyQt5 import QtWidgets


class CountMonitor:

    def __init__(self, ctr_client: si_tt.Client, ui='count_monitor_flex', logger_client=None, server_port=None, config=None):
        """ Constructor for CountMonitor script

        :param ctr_client: instance of hardware client for counter
        :param gui_client: (optional) instance of client of desired output GUI
        :param logger_client: (obj) instance of logger client.
        :param server_port: (int) port number of script server
        """

        self._ctr = ctr_client
        self.log = logger_client
        self._bin_width = None
        self._n_bins = None
        self._ch_list = None
        self._plot_list = None  # List of channels to assign to each plot (e.g. [[1,2], [3,4]])
        self._plots_assigned = []  # List of plots on the GUI that have been assigned

        # Instantiate GUI window
        self.gui = Window(
            gui_template=ui,
            host=get_ip(),
            port=server_port,
            log=self.log
        )

        # Setup stylesheet.
        self.gui.apply_stylesheet()

        # Load config
        self.config = {}
        if config is not None:
            self.config = config

        if not 'name' in self.config:
            self.config.update({'name': f'monitor{np.random.randint(1000)}'})

        self.log.info(self.config)
        num_plots = len((self.config['params'])['plot_list'])

        generate_widgets(self, num_plots)

        # Get all GUI widgets
        self.widgets = get_gui_widgets(
            self.gui,
            graph_widget=num_plots,
            number_label=8,
            tt_name_label=1,
            label=8,
            event_button=num_plots,
            legend_widget=num_plots
        )

        if num_plots == 1:
            self.widgets['graph_widget'] = [self.widgets['graph_widget']]
            self.widgets['event_button'] = [self.widgets['event_button']]
            self.widgets['legend_widget'] = [self.widgets['legend_widget']]

    def set_hardware(self, ctr):
        """ Sets hardware client for this script

        :param ctr: instance of count monitor hardware client
        """

        # Initialize counter instance
        self._ctr = ctr

    def set_params(self, bin_width=1e9, n_bins=1e4, ch_list=[1], plot_list=None):
        """ Sets counter parameters

        :param bin_width: bin width in ps
        :param n_bins: number of bins to display on graph
        :param ch_list: (list) channels to record
        :param plot_list: list of channels to assign to each plot (e.g. [[1,2], [3,4]])
        """

        # Save params to internal variables
        self._bin_width = int(bin_width)
        self._n_bins = int(n_bins)
        self._ch_list = ch_list
        self._plot_list = plot_list

    def set_names(self, config):
        """Sets tt and channel names from config dict."""
        if 'tt_name' in config:
            self._tt_name = config['tt_name']
        else:
            self._tt_name = " "
        if 'ch_names' in config:
            self._ch_names = config['ch_names']
        else:
            self._ch_names = {}

    def run(self):
        """ Runs the counter from scratch"""

        try:

            # Start the counter with desired parameters
            self._initialize_display()

            # Give time to initialize
            # time.sleep(0.05)
            self._is_running = True

            self._ctr.start_trace(
                name=self.config['name'],
                ch_list=self._ch_list,
                bin_width=self._bin_width,
                n_bins=self._n_bins
            )

            # Continuously update data until paused
            while self._is_running:
                self._update_output()
                self.gui.force_update()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """ Pauses the counter"""

        self._is_running = False

    def resume(self):
        """ Resumes the counter.

        To be used to resume after the counter has been paused.
        """

        try:
            self._is_running = True

            # Clear counter and resume plotting
            self._ctr.clear_ctr(name=self.config['name'])
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    # Technical methods

    def _initialize_display(self):
        """ Initializes the display (configures all plots) """

        plot_index = 0
        for index in range(len(self.widgets['graph_widget'])):
            # Configure and return legend widgets
            self.widgets['legend_widget'][index] = get_legend_from_graphics_view(
                self.widgets['legend_widget'][index]
            )

        # Set TT name label, will leave blank if not given
        self.widgets['tt_name_label'].setText(f'Time Tagger: {self._tt_name}')

        # Channel name assignment using self._ch_names set by set_names
        ch_names_dict = self._ch_names
        for index in range(len(self.widgets['label'])):
            channel_num = index + 1  # label_1 is for counter 1, etc.
            ch_name = ch_names_dict.get(f"{channel_num}", None)
            if ch_name is None:
                self.widgets[f'label'][index].setText(f'Ch {channel_num}')
            else:
                self.widgets[f'label'][index].setText(f'{ch_name} (Ch {channel_num})')

        # For each channel, assign to the correct plot and create a curve
        for plot_index, plot_entry in enumerate(self._plot_list):

            try:
                plot_entry_length = len(plot_entry)
            except TypeError:
                plot_entry_length = 0

            if plot_entry_length > 0:
                legend_label = ""
                for j, channel in enumerate(plot_entry):
                    if channel not in self._ch_list:
                        self.log.error(f'channel {channel} is in plot_list but not in ch_list!')
                        return KeyError
                        break

                    # Get channel name if available
                    ch_name = None

                    if self._ch_names:
                        ch_name = self._ch_names.get(f"{channel}", None)
                        if ch_name is None or ch_name == "":
                            legend_label += f'Ch {channel} + '
                        else:
                            legend_label += f'{ch_name} (Ch {channel}) + '
                    else:
                        legend_label += f'Ch {channel} + '

                legend_label = legend_label[:-3]

                # Create a curve and store the widget in our dictionary
                self.widgets[f'curve_{plot_index}'] = self.widgets['graph_widget'][plot_index].plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[plot_index])
                )

                self.widgets['legend_widget'][plot_index].addItem(
                    self.widgets[f'curve_{plot_index}'], ' - ' + legend_label)

            else:
                if plot_entry not in self._ch_list:
                    self.log.error(f'channel {plot_entry} is in plot_list but not in ch_list!')
                    return KeyError

                # Get channel name if available
                ch_name = None
                if self._ch_names:
                    ch_name = self._ch_names.get(f"{channel}", None)
                    if ch_name is None or ch_name == "":
                        legend_label = f'Ch {channel} + '
                    else:
                        legend_label = f'{ch_name} (Ch {channel}) + '
                else:
                    legend_label = f'Ch {channel} + '

                    # Create a curve and store the widget in our dictionary
                    self.widgets[f'curve_{plot_index}'] = self.widgets['graph_widget'][plot_index].plot(
                        pen=pg.mkPen(color=self.gui.COLOR_LIST[plot_index])
                    )

                    self.widgets['legend_widget'][plot_index].addItem(
                        self.widgets[f'curve_{plot_index}'], ' - ' + legend_label)

        # Handle button pressing
        from functools import partial

        for plot_index, clear_button in enumerate(self.widgets['event_button']):
            clear_button.clicked.connect(partial(lambda plot_index: self._clear_plot(plot_index), plot_index=plot_index))

    def _clear_plot(self, plot_index):
        """ Clears the curves on a particular plot

        :param plot_index: (int) index of plot to clear
        """

        # First, handle case where combined count channel is clears (very ugly).

        # self.widgets[f'curve_{plot_index}'].setData(
        #     np.ones(self._n_bins) * self.widgets[f'curve_{plot_index}'].yData[-1]
        # )

        self._ctr.clear_ctr(name=self.config['name'])

    def _update_output(self):
        """ Updates the output to all current values"""

        # Update all active channels
        counts = self._ctr.get_counts(name=self.config['name'])
        counts_per_sec = counts * (1e12 / self._bin_width)

        plot_data = np.zeros([len(self._plot_list), self._n_bins])

        for index, count_array in enumerate(counts_per_sec):

            for plot_index, plot_entry in enumerate(self._plot_list):
                if self._ch_list[index] in plot_entry:
                    plot_data[plot_index] += count_array

            # Figure out which plot to assign to
            channel = self._ch_list[index]

            # Update GUI labels
            self.widgets[f'number_label'][channel - 1].setText(str(count_array[-1]))

        # Update GUI curves
        for plot_index, plot_entry in enumerate(self._plot_list):
            self.widgets[f'curve_{plot_index}'].setData(plot_data[plot_index])


def launch(**kwargs):
    """ Launches the count monitor script """

    # logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(
        'monitor_counts',
        kwargs['config'],
        logger
    )

    # Instantiate CountMonitor
    try:
        monitor = CountMonitor(
            ctr_client=find_client(
                clients,
                config,
                client_type='si_tt',
                client_config='standard_ctr',
                logger=logger
            ),
            logger_client=logger,
            server_port=kwargs['server_port'],
            config=config
        )
    except KeyError:
        print('Please make sure the module names for required servers and GUIS are correct.')
        time.sleep(15)
        raise

    monitor.set_params(**config['params'])
    monitor.set_names(config)

    # Run
    monitor.run()


def generate_widgets(self, num_plots):
    """Static method to return systematically named gui widgets for desired number of monitor counts channels"""

    container = getattr(self.gui, 'verticalLayout')

    if num_plots == 1:

        splitter = QtWidgets.QGroupBox()
        splitter_layout = QtWidgets.QVBoxLayout()
        legend = GraphicsView(GraphicsScene())
        legend.setObjectName(f'legend_widget')
        splitter_layout.addWidget(legend)
        button = QtWidgets.QPushButton('Clear Plot')
        button.setObjectName(f'event_button')
        splitter_layout.addWidget(button)
        splitter.setLayout(splitter_layout)

        sub_container = QtWidgets.QGroupBox(f'Plot_1')
        sub_container_layout = QtWidgets.QHBoxLayout()
        graph = PlotWidget()
        graph.setObjectName(f'graph_widget')
        sub_container_layout.addWidget(graph)
        sub_container_layout.addWidget(splitter)
        sub_container.setLayout(sub_container_layout)
        sub_container_layout.setStretch(0, 5)   # graph
        sub_container_layout.setStretch(1, 1)   # legend+button

        container.layout().addWidget(sub_container)

        # set attributes of widgets so they can be accessed with get_gui_widgets()
        setattr(self.gui, f'graph_widget', graph)
        setattr(self.gui, f'legend_widget', legend)
        setattr(self.gui, f'event_button', button)

    else:

        for i in range(num_plots):

            splitter = QtWidgets.QGroupBox()
            splitter_layout = QtWidgets.QVBoxLayout()
            legend = GraphicsView(GraphicsScene())
            legend.setObjectName(f'legend_widget_{i+1}')
            splitter_layout.addWidget(legend)
            button = QtWidgets.QPushButton('Clear Plot')
            button.setObjectName(f'event_button_{i+1}')
            splitter_layout.addWidget(button)
            splitter.setLayout(splitter_layout)

            sub_container = QtWidgets.QGroupBox(f'Plot_{i+1}')
            sub_container_layout = QtWidgets.QHBoxLayout()
            graph = PlotWidget()
            graph.setObjectName(f'graph_widget_{i+1}')
            sub_container_layout.addWidget(graph)
            sub_container_layout.addWidget(splitter)
            sub_container.setLayout(sub_container_layout)
            sub_container_layout.setStretch(0, 5)   # graph
            sub_container_layout.setStretch(1, 1)   # legend+button

            container.layout().addWidget(sub_container)

            # set attributes of widgets so they can be accessed with get_gui_widgets()
            setattr(self.gui, f'graph_widget_{i+1}', graph)
            setattr(self.gui, f'legend_widget_{i+1}', legend)
            setattr(self.gui, f'event_button_{i+1}', button)
