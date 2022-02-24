""" Module for 1D scanning experiments with convenient GUI interface """

import os
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import importlib
import pyqtgraph as pg
import numpy as np

from pylabnet.scripts.sweeper.sweeper import MultiChSweep1D
from pylabnet.network.client_server.sweeper import Service
from pylabnet.gui.pyqt.external_gui import Window, Popup
from pylabnet.utils.helper_methods import (get_gui_widgets, load_script_config,
                                           get_legend_from_graphics_view, add_to_legend, fill_2dlist, generic_save,
                                           unpack_launcher, create_server, pyqtgraph_save, get_ip, set_graph_background, find_client, get_gui_widgets_dummy)
from pylabnet.scripts.sweeper.scan_fit import FitPopup
from scipy.signal import find_peaks

class Controller(MultiChSweep1D):

    def __init__(self, logger=None, channels=['Channel 1'], clients={}, config=None, fast=True):
        """ Instantiates controller (only 1D data supported so far)

        :param logger: instance of LogClient
        :param channels: (list) list of channel names
        :param config: (str) name of config file
        :param fast: (bool) whether to operate in fast mode
            fast mode only updates heat maps at the end of each scan (this speeds things up)
        """
        self.config = load_script_config('scan1d', config, logger=logger)

        if 'sweep_type' in self.config.keys():
            self.sweep_type = self.config['sweep_type']
        else:
            self.sweep_type = 'triangle'

        super().__init__(logger, channels, sweep_type=self.sweep_type)

        self.module = None

        # Instantiate GUI
        self.gui = Window(
            gui_template='scan_1d',
            host=get_ip(),
            max=True,
            log=self.log,
        )
        self.gui_1 = Window(
            gui_template='count_monitor_combined',
            # gui_template='count_monitor',
            # gui_template='dummy_count_monitor',
            host=get_ip(),
            max=True,
            log=self.log,
        )
        self.widgets = get_gui_widgets(self.gui, p_min=1, p_max=1, pts=1, config=1,
                                       graph=2, legend=2, clients=1, exp=1, exp_preview=1, configure=1, run=1,
                                       autosave=1, save_name=1, save=1, reps=1, rep_tracker=1, avg=2)

        num_plots = len(self.config['params']["plot_list_1"])
        num_channel = len(self.config['params']["ch_list_1"])
        self.widgets_1 = get_gui_widgets_dummy(
            self.gui_1,
            graph_widget=num_plots,
            number_label=num_channel,
            event_button=num_plots,
            legend_widget=num_plots
        )

        # Configure default parameters
        self.min = self.widgets['p_min'].value()
        self.max = self.widgets['p_max'].value()
        self.pts = self.widgets['pts'].value()
        self.reps = self.widgets['reps'].value()

        self.data_fwd = []
        self.data_fwd_2nd_reading = [] ### ADDED
        self.data_bwd = []
        self.avg_fwd = []
        self.avg_fwd_2nd_reading = [] ### ADDED
        self.avg_bwd = []
        self.fit_popup = None
        self.p0_fwd = None
        self.p0_bwd = None
        self.x_fwd = self._generate_x_axis()

        self.num_avg  = None
        self.fft_fwd, self.fft_fwd_avg = None, None
        self.fft_bwd, self.fft_bwd_avg = None, None

        if self.sweep_type != 'sawtooth':
            self.x_bwd = self._generate_x_axis(backward=True)
        else:
            self.x_bwd = self._generate_x_axis()
        self.fast = fast

        # Configure list of experiments
        self.widgets['config'].setText(config)

        self.exp_path = self.config['exp_path']
        model = QtWidgets.QFileSystemModel()
        model.setRootPath(self.exp_path)
        model.setNameFilterDisables(False)
        model.setNameFilters(['*.py'])

        self.widgets['exp'].setModel(model)
        self.widgets['exp'].setRootIndex(model.index(self.exp_path))
        self.widgets['exp'].hideColumn(1)
        self.widgets['exp'].hideColumn(2)
        self.widgets['exp'].hideColumn(3)
        self.widgets['exp'].clicked.connect(self.display_experiment)

        # Configure list of clients
        self.clients = clients
        for client_entry in self.config['servers']:
            client_type = client_entry['type']
            client_config = client_entry['config']
            client = find_client(
                clients=self.clients,
                settings=client_config,
                client_type=client_type,
                client_config=client_config,
                logger=self.log
            )
            if (client == None):
                client_name_concat = client_type
                client_item = QtWidgets.QListWidgetItem(client_name_concat)
                client_item.setForeground(Qt.gray)
                client_item.setToolTip(str("Disconnected"))
                self.widgets['clients'].addItem(client_item)

            else:
                self.log.info(client)
                client_name_concat = f"{client_type}_{client_config}"
                client_item = QtWidgets.QListWidgetItem(client_name_concat)
                client_item.setToolTip(str(client))
                self.widgets['clients'].addItem(client_item)

        #Checking for any missing clients, and adding them as greyed out on the list of clients

        # Manually add logger to client
        self.clients['logger'] = logger

        # Configure button
        self.widgets['configure'].clicked.connect(self.configure_experiment)
        self.widgets['run'].clicked.connect(self.run_pressed)
        self.widgets['autosave'].toggled.connect(self._update_autosave)
        self.widgets['save'].pressed.connect(lambda: self.save(
            filename=self.widgets['save_name'].text(),
            directory=self.config['save_path']
        ))
        self.widgets['reps'].valueChanged.connect(self.set_reps)
        self.widgets['avg'][0].clicked.connect(lambda: self._clear_show_trace(0))
        self.widgets['avg'][1].clicked.connect(lambda: self._clear_show_trace(1))
        self.gui.fit.clicked.connect(self.fit_config)

        # Create legends
        self.widgets['curve'] = []
        for index in range(len(self.widgets['graph'])):
            self.widgets['legend'][index] = get_legend_from_graphics_view(
                self.widgets['legend'][index]
            )

        # Configure hmaps
        self.widgets['hmap'] = []
        for index in range(2):

            # Configure Hmap to work the way we want
            hmap = pg.ImageView(view=pg.PlotItem())
            self.gui.graph_layout.insertWidget(2 * index + 1, hmap)
            hmap.setPredefinedGradient('inferno')
            hmap.show()
            hmap.view.setAspectLocked(False)
            hmap.view.invertY(False)
            self.widgets['hmap'].append(hmap)

        # Setup stylesheet.
        self.gui.apply_stylesheet()


    def display_experiment(self, index):
        """ Displays the currently clicked experiment in the text browser

        :param index: (QModelIndex) index of QTreeView for selected file
        """

        filepath = self.widgets['exp'].model().filePath(index)
        if not os.path.isdir(filepath):
            with open(filepath, 'r') as exp_file:
                exp_content = exp_file.read()

            self.widgets['exp_preview'].setText(exp_content)
            self.widgets['exp_preview'].setStyleSheet('font: 12pt "Consolas"; '
                                                      'color: rgb(255, 255, 255); '
                                                      'background-color: #19232D;')
            self.cur_path = self.widgets['exp'].model().filePath(self.widgets['exp'].currentIndex())
            self.exp_name = os.path.split(os.path.basename(self.cur_path))[0]

    def configure_experiment(self):
        """ Configures experiment to be the currently selected item """

        spec = importlib.util.spec_from_file_location(self.exp_name, self.cur_path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

        self.experiment = self.module.experiment
        self.min = self.widgets['p_min'].value()
        self.max = self.widgets['p_max'].value()
        self.pts = self.widgets['pts'].value()

        self.x_fwd = self._generate_x_axis()
        if self.sweep_type != 'sawtooth':
            self.x_bwd = self._generate_x_axis(backward=True)
        else:
            self.x_bwd = self._generate_x_axis()

        # Run any pre-experiment configuration
        try:
            self.module.configure(self)
        except AttributeError:
            pass

        self.log.info(f'Experiment {self.exp_name} configured')
        self.widgets['exp_preview'].setStyleSheet('font: 12pt "Consolas"; '
                                                  'color: rgb(255, 255, 255); '
                                                  'background-color: rgb(50, 50, 50);')

    def run_pressed(self):
        """ Handles button pressing for run and stop """

        if self.widgets['run'].text() == 'Run':
            self.widgets['run'].setStyleSheet('background-color: red')
            self.widgets['run'].setText('Stop')
            self.log.info('Sweep experiment started')
            self.widgets['rep_tracker'].setValue(1)

            # set min and max
            self.min = self.widgets['p_min'].value()
            self.max = self.widgets['p_max'].value()
            self.pts = self.widgets['pts'].value()

            # reset avg
            self.fft_fwd_avg, self.fft_bwd_avg = None, None
            # run
            self.run()
            self.widgets['rep_tracker'].setValue(0)
            self.widgets['reps'].setValue(0)
            self.widgets['run'].setStyleSheet('background-color: green')
            self.widgets['run'].setText('Run')
            for button in self.widgets['avg']:
                button.setText('Avg only')
            self.log.info('Sweep experiment stopped')
        else:
            self.widgets['rep_tracker'].setValue(0)
            self.widgets['reps'].setValue(0)
            for button in self.widgets['avg']:
                button.setText('Avg only')
            self.widgets['run'].setStyleSheet('background-color: green')
            self.widgets['run'].setText('Run')
            self.stop()
            self.log.info('Sweep experiment stopped')

        # # initialize the window_1
        # self._initialize_display_1()

    def save(self, filename=None, directory=None, date_dir=True):
        """ Saves the dataset

        :param filename: (str) name of file identifier
        :param directory: (str) filepath to save to
        :param date_dir: (bool) whether or not to store in date-specific sub-directory
        """

        if filename is None:
            filename = self.widgets['save_name'].text()
        if directory is None:
            directory = self.config['save_path']

        # Save heatmap
        generic_save(
            data=fill_2dlist(self.data_fwd),
            filename=f'{filename}_fwd_scans',
            directory=directory,
            date_dir=date_dir
        )
        pyqtgraph_save(
            widget=self.widgets['hmap'][0].getView(),
            filename=f'{filename}_fwd_scans',
            directory=directory,
            date_dir=date_dir
        )

        # Save average
        generic_save(
            data=np.vstack((self.x_fwd, np.array([self.avg_fwd]))),
            filename=f'{filename}_fwd_avg',
            directory=directory,
            date_dir=date_dir
        )
        pyqtgraph_save(
            widget=self.widgets['graph'][0].getPlotItem(),
            filename=f'{filename}_fwd_avg',
            directory=directory,
            date_dir=date_dir
        )

        if self.sweep_type != 'sawtooth':

            # Save heatmap
            generic_save(
                data=fill_2dlist(self.data_bwd),
                filename=f'{filename}_bwd_scans',
                directory=directory,
                date_dir=date_dir
            )
            pyqtgraph_save(
                widget=self.widgets['hmap'][1].getView(),
                filename=f'{filename}_bwd_scans',
                directory=directory,
                date_dir=date_dir
            )
            # Save average
            generic_save(
                data=np.vstack((self.x_bwd, np.array([self.avg_bwd]))),
                filename=f'{filename}_bwd_avg',
                directory=directory,
                date_dir=date_dir
            )
            pyqtgraph_save(
                widget=self.widgets['graph'][1].getPlotItem(),
                filename=f'{filename}_bwd_avg',
                directory=directory,
                date_dir=date_dir
            )

        '''else:

            if len(self.data_bwd) > 0:
                # Save heatmap
                generic_save(
                    data=fill_2dlist(self.data_bwd),
                    filename=f'{filename}_bwd_scans',
                    directory=directory,
                    date_dir=date_dir
                )
                pyqtgraph_save(
                    widget=self.widgets['hmap'][1].getView(),
                    filename=f'{filename}_bwd_scans',
                    directory=directory,
                    date_dir=date_dir
                )
                # Save average
                generic_save(
                    data = np.vstack((self.x_bwd, np.array([self.avg_bwd]))),
                    filename=f'{filename}_bwd_avg',
                    directory=directory,
                    date_dir=date_dir
                )
                pyqtgraph_save(
                    widget=self.widgets['graph'][1].getPlotItem(),
                    filename=f'{filename}_bwd_avg',
                    directory=directory,
                    date_dir=date_dir
                )'''

    def fit_config(self, status: bool):
        """ Configures fitting add-on

        :param status: (bool) whether or not fit button is checked
        """

        # If box is newly checked, instantiate popup
        if status:
            self.fit_popup = FitPopup(ui='fit_popup',
                                      x_fwd=self.x_fwd,
                                      data_fwd=self.avg_fwd,
                                      x_bwd=self.x_bwd,
                                      data_bwd=self.avg_bwd,
                                      p0_fwd=None,
                                      p0_bwd=None,
                                      config=self.config,
                                      log=self.log)
            self.fit_popup.model_type.activated.connect(self.fit_popup.fit_selection)
            '''
            if len(self.avg_fwd) != 0:
                    self.fit_popup = FitPopup(ui='fit_popup', data = self.avg_fwd, log=self.log)
                    self.fit_popup.model_type.activated.connect(self.fit_popup.fit_selection)
            else:
                self.fit_error = Popup(ui = 'fit_error')
            '''
        # If box isn't checked, remove popup
        else:
            self.fit_popup = None

    def _configure_plots(self, plot=True):
        """ Configures the plots """

        # Clear plots
        if len(self.widgets['curve']) > 0:
            # self.widgets['curve'][0].clear()
            # self.widgets['curve'][1].clear()
            self.widgets['graph'][0].getPlotItem().clear()
            self.widgets['graph'][1].getPlotItem().clear()
            self.widgets['hmap'][0].clear()
            self.widgets['hmap'][1].clear()
            self.widgets['legend'][0].clear()
            self.widgets['legend'][1].clear()
            self.widgets['curve_avg'][0].clear()
            self.widgets['curve_avg'][1].clear()
            self.widgets['fit_avg'][0].clear()
            self.widgets['fit_avg'][1].clear()
            self.data_fwd = []
            self.data_bwd = []
            self.avg_fwd = []
            self.avg_bwd = []
            self.fit_fwd = []
            self.fit_bwd = []
            self.p0_fwd = None
            self.p0_bwd = None
            self.x_fwd = self._generate_x_axis()
            if self.sweep_type != 'sawtooth':
                self.x_bwd = self._generate_x_axis(backward=True)
            else:
                self.x_bwd = self._generate_x_axis()

        self.widgets['curve'] = []
        self.widgets['curve_avg'] = []
        self.widgets['fit_avg'] = []

        for index, graph in enumerate(self.widgets['graph']):

            if self.sweep_type != 'sawtooth':
                self.widgets['curve'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[6])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['curve'][index],
                    f'{"Fwd" if index==0 else "Bwd"} trace'
                )

                self.widgets['curve_avg'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['curve_avg'][index],
                    f'{"Fwd" if index==0 else "Bwd"} avg'
                )

                self.widgets['fit_avg'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['fit_avg'][index],
                    f'{"Fwd" if index==0 else "Bwd"} fit avg'
                )
            else:
                self.widgets['curve'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[6])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['curve'][index],
                    f'{"1st" if index==0 else "2nd"} trace'
                )

                self.widgets['curve_avg'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['curve_avg'][index],
                    f'{"1st" if index==0 else "2nd"} avg'
                )

                self.widgets['fit_avg'].append(graph.plot(
                    pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
                ))
                add_to_legend(
                    self.widgets['legend'][index],
                    self.widgets['fit_avg'][index],
                    f'{"1st" if index==0 else "2nd"} fit avg'
                )

        for hmap in self.widgets['hmap']:
            hmap.view.setLimits(xMin=self.min, xMax=self.max)

    def _reset_plots(self):
        """ Resets things after a rep """
        self.data_bwd.append([])
        self.data_fwd.append([])

    def _run_and_plot(self, x_value, backward=False):

        if self.sweep_type != 'sawtooth':
            if backward:

                # Single trace
                self.data_bwd[-1].append(self.experiment(x_value, self, gui=self.gui))
                cur_ind = len(self.data_bwd[-1])
                self.widgets['curve'][1].setData(
                    self.x_bwd[:cur_ind],
                    self.data_bwd[-1]
                )


                # Update average and plot
                try:
                    cur_rep = len(self.data_bwd)
                    self.avg_bwd[cur_ind - 1] = (
                        (cur_rep - 1) * self.avg_bwd[cur_ind - 1]
                        + self.data_bwd[-1][-1]
                    ) / cur_rep
                    self.widgets['curve_avg'][1].setData(
                        self.x_bwd,
                        self.avg_bwd
                    )

                # If it is the first run, just add the data
                except IndexError:
                    self.avg_bwd.append(self.data_bwd[-1][-1])

                # Heat map
                if not self.fast:
                    self.widgets['hmap'][1].setImage(
                        img=np.transpose(np.fliplr(fill_2dlist(self.data_bwd))),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )
            else:

                self.data_fwd[-1].append(self.experiment(x_value, self, gui=self.gui))
                cur_ind = len(self.data_fwd[-1])
                self.widgets['curve'][0].setData(
                    self.x_fwd[:cur_ind],
                    self.data_fwd[-1]
                )

                # Update average and plot
                try:
                    cur_rep = len(self.data_fwd)
                    self.avg_fwd[cur_ind - 1] = (
                        (cur_rep - 1) * self.avg_fwd[cur_ind - 1]
                        + self.data_fwd[-1][-1]
                    ) / cur_rep
                    self.widgets['curve_avg'][0].setData(
                        self.x_fwd,
                        self.avg_fwd
                    )


                # If it is the first run, just add the data
                except IndexError:
                    self.avg_fwd.append(self.data_fwd[-1][-1])

                # Heat map
                if not self.fast:
                    self.widgets['hmap'][0].setImage(
                        img=np.transpose(fill_2dlist(self.data_fwd)),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )

        else:
            reading = self.experiment(x_value, self, gui=self.gui)
            try:
                n_readings = len(reading)
                self.data_fwd[-1].append(reading[0])
                cur_ind = len(self.data_fwd[-1])
                self.widgets['curve'][0].setData(
                    self.x_fwd[:cur_ind],
                    self.data_fwd[-1]
                )


                # Update average and plot
                try:
                    cur_rep = len(self.data_fwd)
                    self.avg_fwd[cur_ind - 1] = (
                        (cur_rep - 1) * self.avg_fwd[cur_ind - 1]
                        + self.data_fwd[-1][-1]
                    ) / cur_rep
                    self.widgets['curve_avg'][0].setData(
                        self.x_fwd,
                        self.avg_fwd
                    )

                # If it is the first run, just add the data
                except IndexError:
                    self.avg_fwd.append(self.data_fwd[-1][-1])

                # Heat map
                if not self.fast:
                    self.widgets['hmap'][0].setImage(
                        img=np.transpose(fill_2dlist(self.data_fwd)),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )
                    self.widgets['hmap'][1].setImage(
                        img=np.transpose(fill_2dlist(self.data_bwd)),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )

                self.data_bwd[-1].append(reading[1])
                cur_ind = len(self.data_bwd[-1])
                self.widgets['curve'][1].setData(
                    self.x_bwd[:cur_ind],
                    self.data_bwd[-1]
                )


                # Update average and plot
                try:
                    cur_rep = len(self.data_bwd)
                    self.avg_bwd[cur_ind - 1] = (
                        (cur_rep - 1) * self.avg_bwd[cur_ind - 1]
                        + self.data_bwd[-1][-1]
                    ) / cur_rep
                    self.widgets['curve_avg'][1].setData(
                        self.x_bwd,
                        self.avg_bwd
                    )

                # If it is the first run, just add the data
                except IndexError:
                    self.avg_bwd.append(self.data_bwd[-1][-1])

                # Heat map
                if not self.fast:
                    self.widgets['hmap'][1].setImage(
                        img=np.transpose(np.fliplr(fill_2dlist(self.data_bwd))),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )
            except TypeError:
                self.data_fwd[-1].append(reading)
                cur_ind = len(self.data_fwd[-1])
                self.widgets['curve'][0].setData(
                    self.x_fwd[:cur_ind],
                    self.data_fwd[-1]
                )

                # Update average and plot
                try:
                    cur_rep = len(self.data_fwd)
                    self.avg_fwd[cur_ind - 1] = (
                        (cur_rep - 1) * self.avg_fwd[cur_ind - 1]
                        + self.data_fwd[-1][-1]
                    ) / cur_rep
                    self.widgets['curve_avg'][0].setData(
                        self.x_fwd,
                        self.avg_fwd
                    )

                # If it is the first run, just add the data
                except IndexError:
                    self.avg_fwd.append(self.data_fwd[-1][-1])

                # Heat map
                if not self.fast:
                    self.widgets['hmap'][0].setImage(
                        img=np.transpose(fill_2dlist(self.data_fwd)),
                        pos=(self.min, 0),
                        scale=((self.max - self.min) / self.pts, 1),
                        autoRange=False
                    )

        self.gui.force_update()

    def _update_hmaps(self, reps_done):
        """ Updates hmap if in fast mode """

        if self.fast:
            if self.sweep_type == 'triangle':
                self.widgets['hmap'][1].setImage(
                    img=np.transpose(np.fliplr(fill_2dlist(self.data_bwd))),
                    pos=(self.min, 0),
                    scale=((self.max - self.min) / self.pts, 1),
                    autoRange=False
                )
            self.widgets['hmap'][0].setImage(
                img=np.transpose(fill_2dlist(self.data_fwd)),
                pos=(self.min, 0),
                scale=((self.max - self.min) / self.pts, 1),
                autoRange=False
            )

        # find forward peak number, and use a sliding-window-like way to find numbers 
        # peaks, _ = find_peaks(self.data_fwd[-1], height=[0.1,0.16], distance=80, width=10)
        peaks, _ = find_peaks(self.data_fwd[-1], height=[0.12,0.16], distance=self.pts/(self.max-self.min)*4E-6, width=self.pts/(self.max-self.min)*5E-7)
        dips, _ = find_peaks(-1*np.array(self.data_fwd[-1]), height=[-0.08,0.], distance=self.pts/(self.max-self.min)*4E-6, width=self.pts/(self.max-self.min)*5E-7)
        num_fwd = 0
        if(len(peaks) > 0 and len(dips) > 0):
            ptr_dips, ptr_peaks, ptr_ispeak, ans_q = 0, 0, (peaks[0] <= dips[0]), []
            cur_idx = min(peaks[0] , dips[0])
            while((ptr_dips < len(dips)) and (ptr_peaks < len(peaks))):
                if(ptr_ispeak):
                    # add a dip if it's index is larger than the current index 
                    if(dips[ptr_dips] < cur_idx):
                        ptr_dips += 1
                    else:
                        ans_q += [dips[ptr_dips]]
                        cur_idx = dips[ptr_dips]
                        ptr_dips += 1
                        ptr_ispeak = False
                else:
                    # add a peak if it's index is larger than the current index 
                    if(peaks[ptr_peaks] < cur_idx):
                        ptr_peaks += 1
                    else:
                        ans_q += [peaks[ptr_peaks]]
                        cur_idx = peaks[ptr_peaks]
                        ptr_peaks += 1
                        ptr_ispeak = True

            num_fwd = len(ans_q )/2

        self.log.info('fwd peaks =' + str(self.x_fwd[peaks]))
        self.log.info('num_fwd=' + str(num_fwd))

        # find backward peak number, and use a sliding-window-like way to find numbers 
        peaks, _ = find_peaks(self.data_bwd[-1], height=[0.1,0.16], distance=self.pts/(self.max-self.min)*2E-6, width=self.pts/(self.max-self.min)*3E-7)
        dips, _ = find_peaks(-1*np.array(self.data_bwd[-1]), height=[-0.06,0.], distance=self.pts/(self.max-self.min)*2E-6, width=self.pts/(self.max-self.min)*3E-7)
        
        num_bwd = 0
        if(len(peaks) > 0 and len(dips) > 0):
            ptr_dips, ptr_peaks, ptr_ispeak, ans_q = 0, 0, (peaks[0] <= dips[0]), []
            cur_idx = min(peaks[0] , dips[0])
            while((ptr_dips < len(dips)) and (ptr_peaks < len(peaks))):
                if(ptr_ispeak):
                    # add a dip if it's index is larger than the current index 
                    if(dips[ptr_dips] < cur_idx):
                        ptr_dips += 1
                    else:
                        ans_q += [dips[ptr_dips]]
                        cur_idx = dips[ptr_dips]
                        ptr_dips += 1
                        ptr_ispeak = False
                else:
                    # add a peak if it's index is larger than the current index 
                    if(peaks[ptr_peaks] < cur_idx):
                        ptr_peaks += 1
                    else:
                        ans_q += [peaks[ptr_peaks]]
                        cur_idx = peaks[ptr_peaks]
                        ptr_peaks += 1
                        ptr_ispeak = True
            num_bwd = len(ans_q)/2

        
        self.log.info('bwd peaks =' + str(self.x_bwd[peaks]))
        self.log.info('num_bwd=' + str(num_bwd))

        self.log.info('num_avg=' + str( (num_fwd + num_bwd)/2.   ))
        self.num_avg = (num_fwd + num_bwd)/2.

        # FFT
        self.fft_fwd = np.fft.fft(self.data_fwd[-1])
        self.fft_bwd = np.fft.fft(self.data_bwd[-1])

        # update gui_1
        self._update_output_1()
        # self.gui.force_update()
        return










    def _update_integrated(self, reps_done):
        """ Update repetition counter """

        self.widgets['rep_tracker'].setValue(reps_done + 1)
        self._update_fits()

    def _update_fits(self):
        """ Updates fits """
        if len(self.avg_fwd) != 0 and self.fit_popup is not None:
            if self.fit_popup.mod is not None and\
                    self.fit_popup.mod.init_params is not None:
                self.fit_popup.data_fwd = np.array(self.avg_fwd)
                self.fit_popup.data_bwd = np.array(self.avg_bwd)
                if self.p0_fwd is not None and self.p0_bwd is not None:
                    self.fit_popup.p0_fwd = self.p0_fwd
                    self.fit_popup.p0_bwd = self.p0_bwd
                #method = getattr(self.fit_popup, self.fit_popup.fit_method)
                self.fit_fwd, self.fit_bwd, self.p0_fwd, self.p0_bwd = self.fit_popup.fit_mod()
                if self.fit_popup.fit_suc:
                    self.widgets['fit_avg'][0].setData(
                        self.x_fwd,
                        self.fit_fwd
                    )
                    self.widgets['fit_avg'][1].setData(
                        self.x_bwd,
                        self.fit_bwd
                    )
                #print(self.avg_fwd)
        else:
            pass
        #print(self.config)

    def _update_autosave(self):
        """ Updates autosave status """

        self.autosave = self.widgets['autosave'].isChecked()

    def _clear_show_trace(self, index):
        """ Clears or shows the single scan trace of a graph

        :param index: (int) index of graph
        """

        # Check status of button
        try:
            if self.widgets['avg'][index].text() == 'Avg only':
                self.widgets['avg'][index].setText('Show trace')
                self.widgets['graph'][index].removeItem(self.widgets['curve'][index])
            else:
                self.widgets['avg'][index].setText('Avg only')
                self.widgets['graph'][index].addItem(self.widgets['curve'][index])
        except KeyError:
            pass


    def _initialize_display_1(self):
        """ Initializes the display (configures all plots) """

        plot_index = 0
        for index in range(len(self.widgets_1['graph_widget'])):
            # Configure and return legend widgets
            self.widgets_1['legend_widget'][index] = get_legend_from_graphics_view(
                self.widgets_1['legend_widget'][index]
            )

        for color, channel in enumerate(self._ch_list_1):

            # Figure out which plot to assign to
            if self._plot_list_1 is not None:
                for index, channel_set in enumerate(self._plot_list_1):
                    if channel in channel_set:
                        plot_index = index
                        break

            # Create a curve and store the widget in our dictionary
            self.widgets_1[f'curve_{channel}'] = self.widgets_1['graph_widget'][plot_index].plot(
                pen=pg.mkPen(color=self.gui.COLOR_LIST[color])
            )
            self.widgets_1['legend_widget'][plot_index].addItem(
                self.widgets_1[f'curve_{channel}'],
                ' - ' + f'Channel {channel}'
            )

            # Assign scalar
            # self.gui_handler.assign_label(
            #     label_widget=self._number_widgets[channel - 1],
            #     label_label='Channel {}'.format(channel)
            # )

        # Handle button pressing
        from functools import partial

        for plot_index, clear_button in enumerate(self.widgets_1['event_button']):
            clear_button.clicked.connect(partial(lambda plot_index: self._clear_plot_1(plot_index), plot_index=plot_index))


    def set_params_1(self, bin_width_1=1e9, n_bins_1=1e3, ch_list_1=[1], plot_list_1=[[1]]):
        """ Sets counter parameters

        :param bin_width: bin width in ps
        :param n_bins: number of bins to display on graph
        :param ch_list: (list) channels to record
        :param plot_list: list of channels to assign to each plot (e.g. [[1,2], [3,4]])
        """


        # Save params to internal variables
        self._bin_width_1 = int(bin_width_1)
        self._n_bins_1 = int(n_bins_1)
        self._ch_list_1 = ch_list_1
        self._plot_list_1 = plot_list_1
        self.data_1 = np.zeros(self._n_bins_1)


    def _clear_plot_1(self, plot_index):
        """ Clears the curves on a particular plot

        :param plot_index: (int) index of plot to clear
        """

        # Find all curves in this plot
        for channel in self._plot_list_1[plot_index]:

            # Set the curve to constant with last point for all entries
            self.data_1 = np.ones(self._n_bins_1) * self.widgets_1[f'curve_{channel}'].yData[-1]


            self.widgets_1[f'curve_{channel}'].setData(
                self.data_1
            )
    def _update_output_1(self):
        """ Updates the output to all current values"""

        # 1, Figure out which plot to assign to
        channel = self._ch_list_1[0]
        self.data_1 = np.concatenate((self.data_1[1:], np.array([self.num_avg ])))
        self.widgets_1[f'curve_{channel}'].setData( self.data_1)
        self.widgets_1[f'number_label'][channel - 1].setText(str(  format(self.data_1[-1], ".5f")   ))

        # 2, FFT
        channel = self._ch_list_1[1]
        self.widgets_1[f'curve_{channel}'].setData( np.absolute(self.fft_fwd) )
        self.widgets_1[f'number_label'][channel - 1].setText(str(  format(np.absolute(self.fft_fwd)[-1], ".5f")   ))

        channel = self._ch_list_1[2]
        self.widgets_1[f'curve_{channel}'].setData( np.absolute(self.fft_bwd) )
        self.widgets_1[f'number_label'][channel - 1].setText(str(  format(np.absolute(self.fft_bwd)[-1], ".5f")   ))

        # 2, FFT-avg
        if(self.fft_fwd_avg is None):
            self.fft_fwd_avg = np.array(self.fft_fwd)
        else:
            self.fft_fwd_avg += np.array(self.fft_fwd)

        if(self.fft_bwd_avg is None):
            self.fft_bwd_avg = np.array(self.fft_bwd)
        else:
            self.fft_bwd_avg += np.array(self.fft_bwd)

        channel = self._ch_list_1[3]
        self.widgets_1[f'curve_{channel}'].setData( np.absolute(self.fft_fwd_avg) )
        self.widgets_1[f'number_label'][channel - 1].setText(str(  format(np.absolute(self.fft_fwd_avg)[-1], ".5f")   ))

        channel = self._ch_list_1[4]
        self.widgets_1[f'curve_{channel}'].setData( np.absolute(self.fft_bwd_avg) )
        self.widgets_1[f'number_label'][channel - 1].setText(str(  format(np.absolute(self.fft_bwd_avg)[-1], ".5f")   ))

        # for index, d in enumerate(data):

        #     # Figure out which plot to assign to
        #     channel = self._ch_list_1[index]

        #     d = np.array([d])
        #     self.data_1 = np.concatenate((self.data_1[1:], d))
        #     self.widgets_1[f'curve_{channel}'].setData( self.data_1)
        #     self.widgets_1[f'number_label'][channel - 1].setText(str(  format(self.data_1[-1], ".5f")   ))



def main():

    # Name of config file
    # NOTE: needs to be changed based on the exact config file you are
    # using within configs/scripts/scan1d
    config_name = 'fake_expt'
    control = Controller(config=config_name)
    control.gui.app.exec_()


def launch(**kwargs):
    """ Launches the sweeper GUI """

    logger = kwargs['logger']
    clients = kwargs['clients']

    # Instantiate Monitor script
    control = Controller(
        logger=logger,
        clients=clients,
        config=kwargs['config'],
    )

    update_service = kwargs['service']
    update_service.assign_module(module=control)
    update_port = kwargs['server_port']
    control.gui.set_network_info(port=update_port)

    # set params for gui_1
    control.set_params_1(**control.config['params'])

    # initialize the window_1
    control._initialize_display_1()

    control.gui.app.exec_()


if __name__ == '__main__':
    main()
