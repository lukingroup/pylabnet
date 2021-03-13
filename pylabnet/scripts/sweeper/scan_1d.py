""" Module for 1D scanning experiments with convenient GUI interface """

import os
import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import importlib
import pyqtgraph as pg
import numpy as np

from pylabnet.scripts.sweeper.sweeper import MultiChSweep1D
from pylabnet.network.client_server.sweeper import Service
from pylabnet.gui.pyqt.external_gui import Window, Popup
from pylabnet.utils.helper_methods import (get_gui_widgets, load_script_config,
    get_legend_from_graphics_view, add_to_legend, fill_2dlist, generic_save,
    unpack_launcher, create_server, pyqtgraph_save, get_ip, set_graph_background)
from pylabnet.scripts.sweeper.scan_fit import FitPopup


class Controller(MultiChSweep1D):

    def __init__(self, logger=None, channels=['Channel 1'], clients={}, config=None, fast=True):
        """ Instantiates controller (only 1D data supported so far)

        :param logger: instance of LogClient
        :param channels: (list) list of channel names
        :param config: (str) name of config file
        :param fast: (bool) whether to operate in fast mode
            fast mode only updates heat maps at the end of each scan (this speeds things up)
        """

        super().__init__(logger, channels)
        self.module = None

        # Instantiate GUI
        self.gui = Window(
            gui_template='scan_1d',
            host=get_ip(),
            max=True
        )
        self.widgets = get_gui_widgets(self.gui, p_min=1, p_max=1, pts=1, config=1,
            graph=2, legend=2, clients=1, exp=1, exp_preview=1, configure=1, run=1,
            autosave=1, save_name=1, save=1, reps=1, rep_tracker=1, avg=2)
    
        
        # Configure default parameters
        self.min = self.widgets['p_min'].value()
        self.max = self.widgets['p_max'].value()
        self.pts = self.widgets['pts'].value()
        self.reps = self.widgets['reps'].value()

        self.data_fwd = []
        self.data_bwd = []
        self.avg_fwd = []
        self.avg_bwd = []
        self.fit_popup = None
        self.p0_fwd = None
        self.p0_bwd = None
        self.x_fwd = self._generate_x_axis()
        self.x_bwd = self._generate_x_axis(backward=True)
        self.fast = fast

        # Configure list of experiments
        self.widgets['config'].setText(config)
        self.config = load_script_config('scan1d', config, logger=self.log)

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
        for client_name, client_obj in self.clients.items():
            client_name_concat = '-'.join(client_name)
            client_item = QtWidgets.QListWidgetItem(client_name_concat)
            client_item.setToolTip(str(client_obj))
            self.widgets['clients'].addItem(client_item)

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
            self.gui.graph_layout.insertWidget(2*index+1, hmap)
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
        self.x_bwd = self._generate_x_axis(backward=True)

        # Run any pre-experiment configuration
        try:
            self.module.configure(self.clients)
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
            data = np.vstack((self.x_fwd, np.array([self.avg_fwd]))),
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
            )

    def fit_config(self, status:bool):
        """ Configures fitting add-on

        :param status: (bool) whether or not fit button is checked
        """

        # If box is newly checked, instantiate popup
        if status:
            self.fit_popup = FitPopup(ui='fit_popup',
                                      x_fwd = self.x_fwd,
                                      data_fwd = self.avg_fwd,
                                      x_bwd = self.x_bwd,
                                      data_bwd = self.avg_bwd,
                                      p0_fwd = None,
                                      p0_bwd = None,
                                      config = self.config,
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
            self.x_bwd = self._generate_x_axis(backward=True)

        self.widgets['curve'] = []
        self.widgets['curve_avg'] = []
        self.widgets['fit_avg'] = []

        for index, graph in enumerate(self.widgets['graph']):

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

        for hmap in self.widgets['hmap']:
            hmap.view.setLimits(xMin=self.min, xMax=self.max)

    def _reset_plots(self):
        """ Resets things after a rep """
        self.data_bwd.append([])
        self.data_fwd.append([])

    def _run_and_plot(self, x_value, backward=False):

        if backward:

            # Single trace
            self.data_bwd[-1].append(self.experiment(x_value, self.clients, gui=self.gui))
            cur_ind = len(self.data_bwd[-1])
            self.widgets['curve'][1].setData(
                self.x_bwd[:cur_ind],
                self.data_bwd[-1]
            )

            # Update average and plot
            try:
                cur_rep = len(self.data_bwd)
                self.avg_bwd[cur_ind-1] = (
                    (cur_rep-1) * self.avg_bwd[cur_ind-1]
                    + self.data_bwd[-1][-1]
                )/cur_rep
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
                    scale=((self.max-self.min)/self.pts,1),
                    autoRange=False
                )
        else:

            self.data_fwd[-1].append(self.experiment(x_value, self.clients, gui=self.gui))
            cur_ind = len(self.data_fwd[-1])
            self.widgets['curve'][0].setData(
                self.x_fwd[:cur_ind],
                self.data_fwd[-1]
            )

            # Update average and plot
            try:
                cur_rep = len(self.data_fwd)
                self.avg_fwd[cur_ind-1] = (
                    (cur_rep-1) * self.avg_fwd[cur_ind-1]
                    + self.data_fwd[-1][-1]
                )/cur_rep
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
                    scale=((self.max-self.min)/self.pts,1),
                    autoRange=False
                )
        self.gui.force_update()

    def _update_hmaps(self, reps_done):
        """ Updates hmap if in fast mode """

        if self.fast:
            self.widgets['hmap'][1].setImage(
                img=np.transpose(np.fliplr(fill_2dlist(self.data_bwd))),
                pos=(self.min, 0),
                scale=((self.max-self.min)/self.pts,1),
                autoRange=False
            )
            self.widgets['hmap'][0].setImage(
                img=np.transpose(fill_2dlist(self.data_fwd)),
                pos=(self.min, 0),
                scale=((self.max-self.min)/self.pts,1),
                autoRange=False
            )

    def _update_integrated(self, reps_done):
        """ Update repetition counter """

        self.widgets['rep_tracker'].setValue(reps_done + 1)
        self._update_fits()

    def _update_fits(self):
        """ Updates fits """
        if len(self.avg_fwd) != 0 and self.fit_popup is not None:
            if self.fit_popup.fit_method is not None:
                self.fit_popup.data_fwd = np.array(self.avg_fwd)
                self.fit_popup.data_bwd = np.array(self.avg_bwd)
                if self.p0_fwd is not None and self.p0_bwd is not None:
                    self.fit_popup.p0_fwd = self.p0_fwd
                    self.fit_popup.p0_bwd = self.p0_bwd
                method = getattr(self.fit_popup, self.fit_popup.fit_method)
                self.fit_fwd, self.fit_bwd, self.p0_fwd, self.p0_bwd = method()
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


def main():
    
    # Name of config file
    # NOTE: needs to be changed based on the exact config file you are
    # using within configs/scripts/scan1d
    config_name = 'fake_expt'
    control=Controller(config=config_name)
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

    control.gui.app.exec_()


if __name__ == '__main__':
    main()
