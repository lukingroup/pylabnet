""" Module for 1D scanning experiments with convenient GUI interface """

import socket
import os
import sys
from PyQt5 import QtWidgets, QtGui
import importlib
import pyqtgraph as pg
import numpy as np

from pylabnet.scripts.sweeper.sweeper import MultiChSweep1D
from pylabnet.network.client_server.sweeper import Service
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (get_gui_widgets, load_config,
    get_legend_from_graphics_view, add_to_legend, fill_2dlist, generic_save,
    unpack_launcher, create_server, pyqtgraph_save)


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
            host=socket.gethostbyname(socket.gethostname())
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
        self.x_fwd = self._generate_x_axis()
        self.x_bwd = self._generate_x_axis(backward=True)
        self.fast = fast

        # Configure list of experiments
        self.widgets['config'].setText(config)
        self.config = load_config(config, logger=self.log)

        self.exp_path = self.config['exp_path']
        if self.exp_path is None:
            self.exp_path = os.getcwd()
        sys.path.insert(1, self.exp_path)
        for filename in os.listdir(self.exp_path):
            if filename.endswith('.py'):
                self.widgets['exp'].addItem(filename[:-3])
        self.widgets['exp'].itemClicked.connect(self.display_experiment)

        # Configure list of clients
        self.clients = clients
        for client_name, client_obj in self.clients.items():
            client_item = QtWidgets.QListWidgetItem(client_name)
            client_item.setToolTip(str(client_obj))
            self.widgets['clients'].addItem(client_item)

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

    def display_experiment(self, item):
        """ Displays the currently clicked experiment in the text browser

        :param item: (QlistWidgetItem) with label of name of experiment to display
        """

        with open(os.path.join(self.exp_path, f'{item.text()}.py'), 'r') as exp_file:
            exp_content = exp_file.read()

        self.widgets['exp_preview'].setText(exp_content)
        self.widgets['exp_preview'].setStyleSheet('font: 12pt "Consolas"; '
                                                  'color: rgb(255, 255, 255); '
                                                  'background-color: rgb(0, 0, 0);')

    def configure_experiment(self):
        """ Configures experiment to be the currently selected item """

        # Set all experiments to normal state and highlight configured expt
        for item_no in range(self.widgets['exp'].count()):
            self.widgets['exp'].item(item_no).setBackground(QtGui.QBrush(QtGui.QColor('black')))
        self.widgets['exp'].currentItem().setBackground(QtGui.QBrush(QtGui.QColor('darkRed')))
        exp_name = self.widgets['exp'].currentItem().text()
        self.module = importlib.import_module(exp_name)
        self.module = importlib.reload(self.module)

        self.experiment = self.module.experiment
        self.min = self.widgets['p_min'].value()
        self.max = self.widgets['p_max'].value()
        self.pts = self.widgets['pts'].value()

        self.x_fwd = self._generate_x_axis()
        self.x_bwd = self._generate_x_axis(backward=True)

        # Run any pre-experiment configuration
        try:
            self.module.configure(**self.clients)
        except AttributeError:
            pass

        self.log.info(f'Experiment {exp_name} configured')
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
            self.data_fwd = []
            self.data_bwd = []
            self.avg_fwd = []
            self.avg_bwd = []
            self.x_fwd = self._generate_x_axis()
            self.x_bwd = self._generate_x_axis(backward=True)

        self.widgets['curve'] = []
        self.widgets['curve_avg'] = []

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

        for hmap in self.widgets['hmap']:
            hmap.view.setLimits(xMin=self.min, xMax=self.max)

    def _reset_plots(self):
        """ Resets things after a rep """
        self.data_bwd.append([])
        self.data_fwd.append([])

    def _run_and_plot(self, x_value, backward=False):

        if backward:

            # Single trace
            self.data_bwd[-1].append(self.experiment(x_value, **self.clients, gui=self.gui))
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

            self.data_fwd[-1].append(self.experiment(x_value, **self.clients, gui=self.gui))
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
    control=Controller(config='laser_scan')
    while True:
        control.gui.force_update()

def launch(**kwargs):
    """ Launches the sweeper GUI """

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    # Instantiate Monitor script
    control = Controller(
        logger=logger,
        clients=clients,
        config=kwargs['config'],
    )

    update_service = Service()
    update_service.assign_module(module=control)
    update_service.assign_logger(logger=logger)
    update_server, update_port = create_server(update_service, logger, host=socket.gethostbyname_ex(socket.gethostname())[2][0])
    logger.update_data(data={'port': update_port})
    control.gui.set_network_info(port=update_port)
    update_server.start()

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        control.gui.force_update()


if __name__ == '__main__':
    main()
