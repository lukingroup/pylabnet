""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import os
import sys
import importlib
import time
from datetime import datetime
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets


REFRESH_RATE = 150   # refresh rate in ms, try increasing if GUI lags


class DataVisualizer:

    def __init__(self, logger=None, client_tuples=None, config=None, config_name=None):

        self.log = LogHandler(logger)
        self.dataset = None

        # Instantiate GUI window
        self.gui = Window(
            gui_template='data_visualizer',
            host=get_ip()
        )

        # Configure list of experiments
        self.gui.config.setText(config_name)
        self.config = config
        self.bare_data_path = self.config['data_path']
       
        # if self.exp_path is None:
        #     self.exp_path = os.getcwd()
        # sys.path.insert(1, self.exp_path)
        # self.update_experiment_list()

        # sys.path.insert(1, self.data_path)
        self.update_date()

        # Configure button clicks
        self.gui.year_val.textChanged.connect(self.update_date)
        self.gui.month_val.textChanged.connect(self.update_date)
        self.gui.day_val.textChanged.connect(self.update_date)

        self.gui.plot.clicked.connect(self.configure)
        self.gui.save.clicked.connect(self.save)

        self.gui.load_config.clicked.connect(self.reload_config)
        self.gui.showMaximized()
        self.gui.apply_stylesheet()

    def update_date(self):
        year = self.gui.year_val.text()
        month = self.gui.month_val.text()
        day = self.gui.day_val.text()

        self.data_path = self.bare_data_path + "\\" + year + "\\" + month + "\\" + day

        if os.path.isdir(self.data_path):
            self.update_data_list()
        else:
            self.gui.y_data.clear()
            self.gui.x_data.clear()
    
    def update_data_list(self):
        """ Updates list of experiments """

        self.gui.y_data.clear()
        self.gui.x_data.clear()
        for filename in os.listdir(self.data_path):
            if filename.endswith('.txt'):
                self.gui.x_data.addItem(filename[:-4])
                self.gui.y_data.addItem(filename[:-4])
        # self.gui.exp.itemClicked.connect(self.display_experiment)

    def configure(self):
        """ Configures the currently selected experiment + dataset """

        # Load the config
        self.reload_config()

        # Set all experiments to normal state and highlight configured expt
        # for item_no in range(self.gui.exp.count()):
        #     self.gui.exp.item(item_no).setBackground(QtGui.QBrush(QtGui.QColor('black')))
        # self.gui.exp.currentItem().setBackground(QtGui.QBrush(QtGui.QColor('darkRed')))
        # exp_name = self.gui.exp.currentItem().text()
        # self.module = importlib.import_module(exp_name)
        # self.module = importlib.reload(self.module)

        # Clear graph area and set up new or cleaned up dataset
        for index in reversed(range(self.gui.graph_layout.count())):
            try:
                self.gui.graph_layout.itemAt(index).widget().deleteLater()
            except AttributeError:
                try:
                    self.gui.graph_layout.itemAt(index).layout().deleteLater()
                except AttributeError:
                    pass
        self.gui.windows = {}

        x_data_name =  self.gui.x_data.currentItem().text()
        y_data_name =  self.gui.y_data.currentItem().text()

        x_data = np.loadtxt(self.data_path + "\\" + x_data_name + ".txt")
        y_data = np.loadtxt(self.data_path + "\\" + y_data_name + ".txt")

        thrsh = self.gui.thrsh_val.value()

        plot_method = self.gui.plot_method.currentItem().text()

        if plot_method is None:
            plot_method = "Standard 1D plot (no x-axis)"

        if plot_method == "Standard 1D plot (no x-axis)":
            self.plot_1D(x_data, y_data, x_axis = False)

        if plot_method == "Standard 1D plot":
            self.plot_1D(x_data, y_data, x_axis = True)

        if plot_method == "Thresholded 1D plot (no x-axis)":
            self.plot_1D_thrsh(x_data, y_data, thrsh = thrsh, x_axis = False)

        if plot_method == "Thresholded 1D plot":
            self.plot_1D_thrsh(x_data, y_data, thrsh = thrsh, x_axis = True)
        
        if plot_method == "Histogram":
            self.plot_hist(x_data, y_data)

        
        # If we're not setting up a new measurement type, just clear the data

        # We are reading in the required base-dataset by looking at the define_dataset() as defined in the experiment script.
        # try:
        #     classname = self.module.define_dataset()
        # except AttributeError:
        #     error_msg = "No 'define_dataset' method found in experiment script."
        #     self.log.error("No 'define_dataset' method found in experiment script.")
        #     return

        # try:
        #     self.dataset = getattr(datasets, classname)(
        #         gui=self.gui,
        #         log=self.log,
        #         config=self.config
        #     )
        # except AttributeError:
        #     error_msg = f"Dataset name {classname} as provided in 'define_dataset' method in experiment script is not valid."
        #     self.log.error(error_msg)
        #     return

        # # Run any pre-experiment configuration
        # try:
        #     self.module.configure(dataset=self.dataset, **self.clients)
        # except AttributeError:
        #     pass
        # self.experiment = self.module.experiment

    def plot_1D(self, x=None, y=None, x_axis = False):

        self.handle_new_window(None)

        color_index = self.gui.graph_layout.count() - 1

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                color_index
            ])
        )

        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y, axis=0)
        else:
            data = y

        if x_axis:
            self.curve.setData(x, data)
        else:
            self.curve.setData(data)

   
    def plot_1D_thrsh(self, x=None, y=None, thrsh=0, x_axis = False):

        self.handle_new_window(None)

        color_index = self.gui.graph_layout.count() - 1

        self.curve = self.graph.plot(
            pen=pg.mkPen(self.gui.COLOR_LIST[
                color_index
            ])
        )

        if np.shape(np.shape(y)) == (2,):
            data = np.mean(y>thrsh, axis=0)
        else:
            data = 1*(y>thrsh)

        if x_axis:
            self.curve.setData(x, data)
        else:
            self.curve.setData(data)

    def plot_hist(self, x=None, y=None):
        pass

    def handle_new_window(self, graph, **kwargs):
        """ Handles visualizing and possibility of new popup windows """

        if graph is None:
            self.graph = self.gui.add_graph()
            #self.graph.getPlotItem().setTitle(self.name)
        
        # Reuse a PlotWidget if provided
        else:
            self.graph = graph
        
    def run(self):
        """ Runs/stops the experiment """

        # Run experiment
        if self.gui.run.text() == 'Run':
            self.gui.run.setStyleSheet('background-color: red')
            self.gui.run.setText('Stop')
            self.log.info('Experiment started')

            # Run update thread
            self.update_thread = UpdateThread(
                autosave=self.gui.autosave.isChecked(),
                save_time=self.gui.autosave_interval.value()
            )
            self.update_thread.data_updated.connect(self.dataset.update)
            self.update_thread.save_flag.connect(self.save)
            self.gui.autosave.toggled.connect(self.update_thread.update_autosave)
            self.gui.autosave_interval.valueChanged.connect(self.update_thread.update_autosave_interval)

            '''
            # Step 2: Create a QThread object
            self.thread = QThread()
            # Step 3: Create a worker object
            self.worker = Worker()
            # Step 4: Move worker to the thread
            self.worker.moveToThread(self.thread)
            # Step 5: Connect signals and slots
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.reportProgress)
            # Step 6: Start the thread
            self.thread.start()

            # Final resets
            self.longRunningBtn.setEnabled(False)
            self.thread.finished.connect(
                lambda: self.longRunningBtn.setEnabled(True)
            )
            self.thread.finished.connect(
                lambda: self.stepLabel.setText("Long-Running Step: 0")
            )
            '''

            self.experiment_thread = ExperimentThread(
                self.experiment,
                dataset=self.dataset,
                gui=self.gui,
                **self.clients
            )

            self.experiment_thread.status_flag.connect(self.dataset.interpret_status)
            self.experiment_thread.finished.connect(self.stop)
            self.log.update_metadata(
                exp_start_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S:%f')
            )

        # Stop experiment
        else:
            self.experiment_thread.running = False

    def stop(self):
        """ Stops the experiment"""

        self.gui.run.setStyleSheet('background-color: green')
        self.gui.run.setText('Run')
        self.log.info('Experiment stopped')
        self.update_thread.running = False

        self.log.update_metadata(
            exp_stop_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S:%f')
        )

        # Autosave if relevant
        if self.gui.autosave.isChecked():
            self.save()

    def save(self):
        """ Saves data """

        self.log.update_metadata(notes=self.gui.notes.toPlainText())
        filename = self.gui.save_name.text()
        directory = self.config['save_path']
        self.dataset.save(
            filename=filename,
            directory=directory,
            date_dir=True
        )
        save_metadata(self.log, filename, directory, True)
        self.log.info('Data saved')

    def reload_config(self):
        """ Loads a new config file """

        self.config = load_script_config(
            script='data_taker',
            config=self.gui.config.text(),
            logger=self.log
        )


class ExperimentThread(QtCore.QThread):
    """ Thread that simply runs the experiment repeatedly """

    # Flag to monitor whether experiment alarm goes off
    status_flag = QtCore.pyqtSignal(str)

    def __init__(self, experiment, **params):
        self.experiment = experiment
        self.params = params
        self.running = True
        super().__init__()
        self.start()

    def run(self):
        self.params['iter_num'] = 0
        while self.running:
            self.experiment(
                thread=self,
                status_flag=self.status_flag,
                **self.params)
            self.params['iter_num'] += 1


class UpdateThread(QtCore.QThread):
    """ Thread that continuously signals GUI to update data """

    data_updated = QtCore.pyqtSignal()
    save_flag = QtCore.pyqtSignal()

    def __init__(self, **kwargs):
        self.running = True
        self.autosave = kwargs['autosave']
        self.save_time = kwargs['save_time']
        super().__init__()
        self.start()

    def update_autosave(self, status: bool):
        """ Updates whether or not to autosave

        :param status: (bool) whether or not to autosave
        """

        self.autosave = status

    def update_autosave_interval(self, interval: int):
        """ Updates autosave interval

        :param interval: (int) duration in seconds for autosave
        """

        self.save_time = interval

    def run(self):
        last_save = time.time()
        while self.running:
            self.data_updated.emit()
            if self.autosave and np.abs(time.time() - last_save) > self.save_time:
                self.save_flag.emit()
                last_save = time.time()
            self.msleep(REFRESH_RATE)


def main():
    control = DataVisualizer(config='preselected_histogram')
    control.gui.app.exec_()


def launch(**kwargs):

    config = load_script_config(
        script='data_visualizer',
        config=kwargs['config'],
        logger=kwargs['logger']
    )

    # Instantiate Monitor script
    control = DataVisualizer(
        logger=kwargs['logger'],
        client_tuples=kwargs['clients'],
        config=config,
        config_name=kwargs['config']
    )
    control.gui.set_network_info(port=kwargs['server_port'])

    # Run continuously
    control.gui.app.exec_()


if __name__ == '__main__':
    main()
