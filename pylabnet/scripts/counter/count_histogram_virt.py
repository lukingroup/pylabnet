from pylabnet.network.client_server import si_tt
from pylabnet.utils.logging.logger import LogClient, LogHandler
from pylabnet.gui.igui.iplot import SingleTraceFig, MultiTraceFig
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (generic_save, get_gui_widgets,
                                           get_legend_from_graphics_view, add_to_legend, create_server, unpack_launcher,
                                           load_config, pyqtgraph_save, find_client, get_ip, load_script_config)
from pylabnet.network.client_server.count_histogram import Service
from pylabnet.scripts.counter.hist_fit import FitPopup

import numpy as np
import time
import pyqtgraph as pg
from PyQt5 import QtWidgets


class TimeTrace:
    """ Convenience class for handling time-trace measurements """

    def __init__(self, ctr: si_tt.Client, log: LogClient,
                 click_ch=1, start_ch=2, binwidth=1000, n_bins=1000, update_interval=0.5,
                 correlation=False, **kwargs):
        """ Instantiates TimeTrace measurement

        :param ctr: (si_tt.Client) client to timetagger hardware
        :param log: (LogClient) instance of logclient for logging
        :param **kwargs: additional keyword arguments including
            :param click_ch: (int) channel receiving clicks
            :param start_ch: (int) channel for starting histogram
            :param binwidth: (int) width of bins in ps
            :param n_bins: (int) total number of bins for histogram
            :param update_interval: (float) interval in seconds to wait between updates
                Note, don't go too small (< 100 ms, not precisely tested yet),
                otherwise we might lag in jupyter notebook
            :param correlation: (bool) whether or not this is correlation meas
            TODO: in future, can implement multiple histograms if useful
        """

        self.ctr = ctr
        self.log = LogHandler(log)

        # Store histogram parameters
        self.click_ch = click_ch
        self.start_ch = start_ch
        self.binwidth = binwidth
        self.n_bins = n_bins

        self.correlation = correlation
        if self.correlation:
            self.hist = f'correlation_{np.random.randint(1000)}'
        else:
            self.hist = f'histogram_{np.random.randint(1000)}'
        self.plot = None
        self.is_paused = False
        self.up_in = update_interval

    def start_acquisition(self):
        """ Begins time-trace acquisition """

        if self.correlation:
            self.ctr.start_correlation(
                name=self.hist,
                ch_1=self.start_ch,
                ch_2=self.click_ch,
                binwidth=self.binwidth,
                n_bins=self.n_bins
            )

        else:

            self.ctr.start_histogram(
                name=self.hist,
                start_ch=self.start_ch,
                click_ch=self.click_ch,
                binwidth=self.binwidth,
                n_bins=self.n_bins
            )

        self.log.info(f'Histogram counter {self.hist} started acquiring'
                      f' with click channel {self.click_ch} and start channel'
                      f' {self.start_ch}')

    def set_parameters(self, binwidth=1000, n_bins=1000, **kwargs):
        """ Updates histogram parameters

        :param binwidth: (int) width of bins in ps
        :param n_bins: (int) total number of bins for histogram
        """

        self.binwidth = binwidth
        self.n_bins = n_bins
        self.log.info('Set parameters for next histogram (will not affect '
                      'any histogram already in progress)')

    def init_plot(self):
        """ Instantiates a plot, assuming counter is live """
        self.plot = SingleTraceFig(title_str='Count Histogram')
        self.plot.set_data(
            x_ar=self.ctr.get_x_axis(self.hist) / 1e12,
            y_ar=self.ctr.get_counts(self.hist)[0]
        )

        self.plot.show()

    def _update_data(self):
        self.plot.set_data(
            y_ar=self.ctr.get_counts(self.hist)[0]
        )

    def go(self):
        """ Runs counter from scratch """

        self.start_acquisition()
        self.init_plot()

        self.is_paused = False
        while not self.is_paused:

            time.sleep(self.up_in)
            self._update_data()

    def resume(self):
        """ Runs an already instantiated counter."""

        self.is_paused = False
        while not self.is_paused:

            time.sleep(self.up_in)
            self._update_data()

    def clear(self):
        """ Clears the data """

        self.ctr.clear_ctr(name=self.hist)

        # self.log.info(f'Counter {self.hist} data cleared')

    def pause(self):
        """ Pauses the go/run loop.

        NOTE: does not actually stop counter acquisition!
        There does not seem to be a way to do that from SI-TT API
        """

        self.is_paused = True

    def save(self, filename=None, directory=None):
        """ Saves the current data """

        generic_save(
            data=np.array([
                self.ctr.get_x_axis(self.hist) / 1e12,
                self.ctr.get_counts(self.hist)[0]
            ]),
            filename=filename,
            directory=directory,
            date_dir=True
        )

        self.log.info('Saved histogram data')


class TimeTraceGui(TimeTrace):
    """ Same as TimeTrace but with a dedicated GUI for display
    and parameter setting"""

    STYLESHEET = 'color: rgb(255, 255, 255); font: 25 12pt "Calibri Light";'

    def __init__(self, ctr: si_tt.Client, log: LogClient, config, ui='histogram', **kwargs):
        """ Instantiates TimeTrace measurement

        :param ctr: (si_tt.Client) client to timetagger hardware
        :param log: (LogClient) instance of logclient for logging
        :param config: (str) name of config file
        :param ui: (str) name of ui file
        :param **kwargs: additional keyword arguments
            TODO: in future, can implement multiple histograms if useful
        """

        # Setup GUI
        self.gui = Window(
            gui_template='histogram',
            host=get_ip(),
            log=log
        )

        # Setup stylesheet.
        self.gui.apply_stylesheet()

        # Store config
        self.config = config

        self.correlation = False
        if 'type' in self.config:
            if self.config['type'] == 'correlation':
                self.correlation = True

        super().__init__(
            ctr=ctr,
            log=log,
            click_ch=self.config['click_ch'],
            start_ch=self.config['start_ch'],
            binwidth=int(self._get_binwidth()),
            n_bins=self.gui.n_bins.value(),
            update_interval=0,
            correlation=self.correlation
        )

        # if not type(self.config['click_ch']) == int:
        #     combined_click_channel = f"{self.config['click_ch'][0]}+{self.config['click_ch'][1]}"
        #     ctr.create_combined_channel(
        #         channel_name=combined_click_channel,
        #         channel_list=self.config['click_ch']
        #     )
        #     self.config['click_ch'] = [combined_click_channel]

        self.gates = {}
        if 'gate_ch' in self.config:

            # Handle singular input
            if not isinstance(self.config['gate_ch'], list):
                self.config['gate_ch'] = [self.config['gate_ch']]

            # Update GUI to handle gates
            self._configure_gui_gates()

            # Setup gated channels
            for gate_ch in self.config['gate_ch']:
                ch_name = f'Gated histogram channel {self.config["click_ch"]} with gate {gate_ch}'
                ctr.create_gated_channel(
                    ch_name,
                    self.config['click_ch'],
                    gate_ch,
                    delay=self.delays[ch_name].value()
                )
                self.gates[ch_name] = TimeTrace(
                    ctr=ctr,
                    log=log,
                    click_ch=ch_name,
                    start_ch=self.config['start_ch'],
                    binwidth=int(self._get_binwidth()),
                    n_bins=self.gui.n_bins.value(),
                    update_interval=0,
                    correlation=self.correlation
                )

        # Configure clicks
        self.gui.configure.clicked.connect(lambda: self.update_parameters(
            binwidth=int(self._get_binwidth()),
            n_bins=self.gui.n_bins.value()
        ))
        self.gui.clear.clicked.connect(self.clear_all)
        # Need Lambda to force it to use default args
        # https://stackoverflow.com/questions/60001583/pyqt5-slot-function-does-not-take-default-argument
        self.gui.save.clicked.connect(lambda: self.save())
        self.gui.run.clicked.connect(self.run)

        #### CHANGED CHANGED CHANGED
        self.gui.fit.clicked.connect(self.fit_config)

        self._configure_delay_updates()

        # Configure window length preview
        self.gui.n_bins.valueChanged.connect(self.update_window_length_label)
        self.gui.binwidth.valueChanged.connect(self.update_window_length_label)

        # Configure window length preview
        self.update_window_length_label()

        # Initialize plot info
        self.curve = self.gui.graph.plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        )

        self.gui.graph.getPlotItem().setLabel('bottom', 'Time (s)')
        self.legend = get_legend_from_graphics_view(self.gui.legend)
        add_to_legend(self.legend, self.curve, 'Histogram')

        self.gate_curves = {}
        index = 1
        for gate in self.gates:
            self.gate_curves[gate] = self.gui.graph.plot(
                pen=pg.mkPen(color=self.gui.COLOR_LIST[index])
            )
            index += 1
            add_to_legend(self.legend, self.gate_curves[gate], gate)

        self.gui.apply_stylesheet()
        self.fitting = False

    def clear_all(self):
        """ Clears all plots """

        self.clear()
        for gate in self.gates.values():
            gate.clear()

    def update_window_length_label(self):
        """ Update label previewing the total window length"""
        binwidth = int(self._get_binwidth()),
        n_bins = self.gui.n_bins.value()

        window_length = binwidth[0] * n_bins # in ps
        self.gui.window_length.setText(f'{window_length/1000} ns')

    def update_parameters(self, binwidth, n_bins):
        """ Updates parameters of all histograms

        :param binwidth: (float) binwidth in ps
        :param n_Bins: (int) total number of bins
        """

        self.set_parameters(binwidth, n_bins)
        for gate in self.gates.values():
            gate.set_parameters(binwidth, n_bins)

    def fit_config(self, status: bool):
        """ Configures fitting add-on

        :param status: (bool) whether or not fit button is checked
        """

        # If box is newly checked, instantiate popup
        if status:
            self.fit_popup = FitPopup(ui='fit_popup_hist',
                                      x=np.array(range(self.gui.n_bins.value())) * int(self._get_binwidth()) / 1e12, #dummy values, not actually used None, #self.ctr.get_x_axis(self.hist)/1e12,
                                      data=np.zeros(self.gui.n_bins.value()), #dummy values, not actually used #None, #self.ctr.get_counts(self.hist)[0],
                                      p0=None,
                                      config=self.config,
                                      log=self.log)
            self.fit_popup.model_type.activated.connect(self.fit_popup.fit_selection)
            self.fit_curve = self.gui.graph.plot(
                pen=pg.mkPen(color=self.gui.COLOR_LIST[5])
            )
            add_to_legend(self.legend, self.fit_curve, 'Histogram Fit')

            self.fitting = True
            self.p0 = None

        # If box isn't checked, remove popup
        else:
            self.fit_popup = None
            self.fitting = False

    def run(self):
        """ Handles run button click """

        if self.gui.run.text() == 'Run':
            self.gui.run.setText('Stop')
            self.gui.run.setStyleSheet('background-color: red')
            self.log.info('Running histogram')
            self.go()
        else:
            self.gui.run.setText('Run')
            self.gui.run.setStyleSheet('background-color: green')
            self.log.info('Stopped histogram')
            if self.gui.autosave.isChecked():
                self.save()
            self.pause()
            for gate in self.gates.values():
                gate.pause()

    def go(self):
        """ Runs counter from scratch """

        self.start_acquisition()
        for gate in self.gates.values():
            gate.start_acquisition()
        self.init_plot()

        self.is_paused = False
        last_save = time.time()
        last_clear = last_save
        while not self.is_paused:

            if self.gui.autosave.isChecked():
                current_time = time.time()
                if current_time - last_save > self.gui.save_time.value():
                    self.save()
                    last_save = current_time
            if self.gui.auto_clear.isChecked():
                current_time = time.time()
                if current_time - last_clear > self.gui.clear_time.value():
                    self.clear_all()
                    last_clear = current_time
            self._update_data()
            self.gui.force_update()

    def init_plot(self):
        """ Initializes the plot """

        # Clear existing data
        self.curve.clear()

        self.curve.setData(
            self.ctr.get_x_axis(self.hist) / 1e12,
            self.ctr.get_counts(self.hist)[0]
        )

        if self.fitting:
            self.fit_curve.clear()

            self._update_fit()

        for gate_name, gate_curve in self.gate_curves.items():
            gate_curve.clear()
            gate_curve.setData(
                self.gates[gate_name].ctr.get_x_axis(self.gates[gate_name].hist) / 1e12,
                self.gates[gate_name].ctr.get_counts(self.gates[gate_name].hist)[0]
            )

    def _update_data(self):
        """ Adds latest data to the plot """

        self.curve.setData(
            self.ctr.get_x_axis(self.hist) / 1e12,
            self.ctr.get_counts(self.hist)[0]
        )

        if self.fitting:
            self._update_fit()

        for gate_name, gate_curve in self.gate_curves.items():
            gate_curve.setData(
                self.gates[gate_name].ctr.get_x_axis(self.gates[gate_name].hist) / 1e12,
                self.gates[gate_name].ctr.get_counts(self.gates[gate_name].hist)[0]
            )

    def _update_fit(self):
        """ Updates fits """
        if self.fit_popup.mod is not None and self.fit_popup.mod.init_params is not None:
            self.fit_popup.data = np.array(self.ctr.get_counts(self.hist)[0])
            self.fit_popup.x = np.array(self.ctr.get_x_axis(self.hist) / 1e12)
            if self.p0 is not None:
                self.fit_popup.p0 = self.p0
            self.fit, self.p0 = self.fit_popup.fit_mod()
            if self.fit_popup.fit_suc:
                self.fit_curve.setData(
                    self.ctr.get_x_axis(self.hist) / 1e12,
                    self.fit
                )

    def _get_binwidth(self):
        """ Gets the binwidth using the unit combo box

        :return: (float) binwidth in ps
        """

        val = self.gui.binwidth.value()
        unit_index = self.gui.units.currentIndex()
        if unit_index == 0:
            return val
        elif unit_index == 1:
            return val * 1e3
        elif unit_index == 2:
            return val * 1e6
        elif unit_index == 3:
            return val * 1e9

    def _configure_gui_gates(self):
        """ Configures the gates part of the GUI """

        # Configure base layout for all gates
        gate_box = QtWidgets.QGroupBox("Gates")
        gate_box.setStyleSheet(self.STYLESHEET)
        vbox = QtWidgets.QVBoxLayout()

        # Now add widgets for each gate
        self.delays = {}
        for index, gate_ch in enumerate(self.config['gate_ch']):

            # Configure widgets
            ch_name = f'Gated histogram channel {self.config["click_ch"]} with gate {gate_ch}'
            hbox = QtWidgets.QHBoxLayout()
            hbox.addWidget(QtWidgets.QLabel(text=f'Gate {gate_ch}'))
            hbox.addWidget(QtWidgets.QLabel(text='Delay: '))
            self.delays[ch_name] = QtWidgets.QDoubleSpinBox()
            self.delays[ch_name].setMaximum(1e12)
            self.delays[ch_name].setSuffix(' ps')
            self.delays[ch_name].setButtonSymbols(2)
            hbox.addWidget(self.delays[ch_name])

            # Check for preconfigured delay and set the value
            if 'delays' in self.config:
                try:
                    self.delays[ch_name].setValue(self.config['delays'][index])
                except IndexError:
                    pass

            # Add to vertical layout
            vbox.addLayout(hbox)

        # Configure layout to a group box and add to GUI in layout
        gate_box.setLayout(vbox)
        self.gui.graph_layout.addWidget(gate_box)

    def _configure_delay_updates(self):
        """ Configures delay updates when a value is changed """

        for channel_name, delay in self.delays.items():
            delay.valueChanged.connect(lambda state, x=channel_name: self.gates[channel_name].ctr.update_delay(
                channel_name=x,
                delay=state
            ))

    def save(self, filename=None, directory=None):
        """ Saves the current data """

        if filename is None:
            filename = self.gui.save_name.text()

        if directory is None:
            directory = self.config['save_path']

        generic_save(
            data=np.array([
                self.ctr.get_x_axis(self.hist) / 1e12,
                self.ctr.get_counts(self.hist)[0]
            ]),
            filename=filename,
            directory=directory,
            date_dir=True
        )

        for gate_name, gate in self.gates.items():
            generic_save(
                data=np.array([
                    gate.ctr.get_x_axis(gate.hist) / 1e12,
                    gate.ctr.get_counts(gate.hist)[0]
                ]),
                filename=gate_name,
                directory=directory,
                date_dir=True
            )

        pyqtgraph_save(
            widget=self.gui.graph.getPlotItem(),
            filename=filename,
            directory=directory,
            date_dir=True
        )

        self.log.info('Saved histogram data')


def launch(**kwargs):
    """ Launches the sweeper GUI """

    # logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(
        'histogram',
        kwargs['config'],
        logger
    )

    ctr = find_client(
        clients,
        config,
        client_type='si_tt',
        client_config='standard_ctr',
        logger=logger
    )

    # Instantiate Monitor script
    trace = TimeTraceGui(
        ctr=ctr,
        log=logger,
        config=config,
    )

    update_service = Service()
    update_service.assign_module(module=trace)
    update_service.assign_logger(logger=logger)
    update_server, update_port = create_server(update_service, logger, host=get_ip())
    logger.update_data(data={'port': update_port})
    trace.gui.set_network_info(port=update_port)
    update_server.start()

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        trace.gui.force_update()
