from pylabnet.network.client_server import si_tt
from pylabnet.utils.logging.logger import LogClient, LogHandler
from pylabnet.gui.igui.iplot import SingleTraceFig
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (generic_save, get_gui_widgets,
    get_legend_from_graphics_view, add_to_legend, create_server, unpack_launcher,
    load_config, pyqtgraph_save)
from pylabnet.network.client_server.count_histogram import Service

import numpy as np
import time
import socket
import pyqtgraph as pg


class TimeTrace:
    """ Convenience class for handling time-trace measurements """

    def __init__(self, ctr: si_tt.Client, log: LogClient,
                 click_ch=1, start_ch=2, binwidth=1000, n_bins=1000, update_interval=0.5, **kwargs):
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
            TODO: in future, can implement multiple histograms if useful
        """

        self.ctr = ctr
        self.log = LogHandler(log)

        # Store histogram parameters
        self.click_ch = click_ch
        self.start_ch = start_ch
        self.binwidth = binwidth
        self.n_bins = n_bins

        self.hist = f'histogram_{np.random.randint(1000)}'
        self.plot = None
        self.is_paused = False
        self.up_in = update_interval

    def start_acquisition(self):
        """ Begins time-trace acquisition """

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
            x_ar=self.ctr.get_x_axis(self.hist)/1e12,
            y_ar=self.ctr.get_counts(self.hist)[0]
        )
        self.plot.show()

    def _update_data(self):
        """ Updates to the current data """

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
                self.ctr.get_x_axis(self.hist)/1e12,
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
            host=socket.gethostbyname(socket.gethostname())
        )

        self.config = load_config(config, logger=log)
        super().__init__(
            ctr=ctr,
            log=log,
            click_ch=self.config['click_ch'],
            start_ch=self.config['start_ch'],
            binwidth=int(self._get_binwidth()),
            n_bins=self.gui.n_bins.value(),
            update_interval=0
        )

        # Configure clicks
        self.gui.configure.clicked.connect(lambda: self.set_parameters(
            binwidth=int(self._get_binwidth()),
            n_bins=self.gui.n_bins.value()
        ))
        self.gui.clear.clicked.connect(self.clear)
        self.gui.save.clicked.connect(lambda: self.save(
            filename=self.gui.save_name.text(),
            directory=self.config['save_path']
        ))
        self.gui.run.clicked.connect(self.run)

        # Initialize plot info
        self.curve = self.gui.graph.plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        )
        self.gui.graph.getPlotItem().setLabel('bottom', 'Time (s)')
        self.legend = get_legend_from_graphics_view(self.gui.legend)
        add_to_legend(self.legend, self.curve, 'Histogram')

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
                self.save(
                    filename=self.gui.save_name.text(),
                    directory=self.config['save_path']
                )
            self.pause()

    def go(self):
        """ Runs counter from scratch """

        self.start_acquisition()
        self.init_plot()

        self.is_paused = False
        last_save = time.time()
        last_clear = last_save
        while not self.is_paused:

            if self.gui.autosave.isChecked():
                current_time = time.time()
                if current_time - last_save > self.gui.save_time.value():
                    self.save(
                        filename=self.gui.save_name.text(),
                        directory=self.config['save_path']
                    )
                    last_save = current_time
            if self.gui.auto_clear.isChecked():
                current_time = time.time()
                if current_time - last_clear > self.gui.clear_time.value():
                    self.clear()
                    last_clear = current_time
            self._update_data()
            self.gui.force_update()

    def init_plot(self):
        """ Initializes the plot """

        # Clear existing data
        self.curve.clear()
        # self.gui.graph.getPlotItem().setLabel('bottom', f'Time {self.gui.units.currentText()}')
        self.curve.setData(
            self.ctr.get_x_axis(self.hist)/1e12,
            self.ctr.get_counts(self.hist)[0]
        )

    def _update_data(self):
        """ Adds latest data to the plot """

        self.curve.setData(
            self.ctr.get_x_axis(self.hist)/1e12,
            self.ctr.get_counts(self.hist)[0]
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
            return val*1e3
        elif unit_index == 2:
            return val*1e6
        elif unit_index == 3:
            return val*1e9

    def save(self, filename=None, directory=None):
        """ Saves the current data """

        generic_save(
            data=np.array([
                self.ctr.get_x_axis(self.hist)/1e12,
                self.ctr.get_counts(self.hist)[0]
            ]),
            filename=filename,
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

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    # Instantiate Monitor script
    trace = TimeTraceGui(
        ctr = clients['si_tt'],
        log=logger,
        config=kwargs['config'],
    )

    update_service = Service()
    update_service.assign_module(module=trace)
    update_service.assign_logger(logger=logger)
    update_server, update_port = create_server(update_service, logger, host=socket.gethostbyname_ex(socket.gethostname())[2][0])
    logger.update_data(data={'port': update_port})
    trace.gui.set_network_info(port=update_port)
    update_server.start()

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        trace.gui.force_update()

