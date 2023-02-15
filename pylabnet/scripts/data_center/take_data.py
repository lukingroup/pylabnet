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

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config, generic_save, unpack_launcher, save_metadata, load_script_config, find_client, get_ip
from pylabnet.scripts.data_center import datasets
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton


REFRESH_RATE = 150   # refresh rate in ms, try increasing if GUI lags


class DataTaker:

    def __init__(self, logger=None, client_tuples=None, config=None, config_name=None):

        self.log = LogHandler(logger)
        self.dataset = None

        # Instantiate GUI window
        self.gui = Window(
            gui_template='data_taker',
            host=get_ip(),
            log=self.log,
        )

        # Configure list of experiments
        self.gui.config.setText(config_name)
        self.config = config
        self.exp_path = self.config['exp_path']
        if self.exp_path is None:
            self.exp_path = os.getcwd()
        sys.path.insert(1, self.exp_path)
        self.update_experiment_list()

        # Configure list of clients
        self.clients = {}

        # Configure list of missing clients
        self.missing_clients = {}

        # Keep track of valid init dict
        self.valid_init_dict = False

        # Setup Autosave
        # First check whether autosave is specified in config file
        if 'auto_save' in self.config:
            if self.config['auto_save']:
                self.gui.autosave.setChecked(True)

        # Retrieve Clients
        for client_entry in self.config['servers']:
            client_type = client_entry['type']
            client_config = client_entry['config']
            client = find_client(
                clients=client_tuples,
                settings=client_config,
                client_type=client_type,
                client_config=client_config,
                logger=self.log
            )

            if (client == None):
                self.missing_clients[f"{client_type}_{client_config}"] = [client_type, client_config]
            else:
                self.clients[f"{client_type}_{client_config}"] = client

        for client_name, client_obj in self.clients.items():
            client_item = QtWidgets.QListWidgetItem(client_name)
            client_item.setToolTip(str(client_obj))
            self.gui.clients.addItem(client_item)

        for client_name, client_config in self.missing_clients.items():
            client_item = QtWidgets.QListWidgetItem(client_name)
            client_item.setForeground(Qt.gray)
            self.gui.clients.addItem(client_item)
            self.log.error("Datataker missing client: " + client_name)

        # Configure button clicks
        self.gui.configure.clicked.connect(self.configure)
        self.gui.run.clicked.connect(self.run)
        self.gui.save.clicked.connect(self.save)
        self.gui.clearData.clicked.connect(self.clear_data)
        self.gui.load_config.clicked.connect(self.reload_config)
        self.gui.showMaximized()
        self.gui.apply_stylesheet()

    def update_experiment_list(self):
        """ Updates list of experiments """

        model = QtWidgets.QFileSystemModel()
        model.setRootPath(self.exp_path)
        model.setNameFilterDisables(False)
        model.setNameFilters(['*.py'])

        self.gui.exp.setModel(model)
        self.gui.exp.setRootIndex(model.index(self.exp_path))
        self.gui.exp.hideColumn(1)
        self.gui.exp.hideColumn(2)
        self.gui.exp.hideColumn(3)
        self.gui.exp.clicked.connect(self.display_experiment)

    def display_experiment(self, index):
        """ Displays the currently clicked experiment in the text browser

        :param index: index of (QTreeView) entry to display
        """

        filepath = self.gui.exp.model().filePath(index)
        if not os.path.isdir(filepath):
            with open(filepath, 'r') as exp_file:
                exp_content = exp_file.read()

            self.gui.exp_preview.setText(exp_content)
            self.gui.exp_preview.setStyleSheet('font: 10pt "Consolas"; '
                                               'color: rgb(255, 255, 255); '
                                               'background-color: rgb(0, 0, 0);')
            self.log.update_metadata(experiment_file=exp_content)

            self.cur_path = self.gui.exp.model().filePath(self.gui.exp.currentIndex())
            self.exp_name = os.path.split(os.path.basename(self.cur_path))[1][:-3]

        self.load_init_dict(index)


    def load_init_dict(self, index):
        """ Displays the currently clicked experiment's init dict

        :param index: index of (QTreeView) entry to display
        """

        filepath = self.gui.exp.model().filePath(index)
        if not os.path.isdir(filepath):
           
            spec = importlib.util.spec_from_file_location("init_dict", filepath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.valid_init_dict = True

            try:
                self.init_dict = mod.INIT_DICT
            except AttributeError:
                self.init_dict = {}
                self.valid_init_dict = False

        self.update_init_form()

    def create_gridlayout(self):

        input_init_scrollarea = self.gui.init_dict_scrollarea

        self.gui.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.gui.input_dict_gridlayout = QtWidgets.QGridLayout(self.gui.scrollAreaWidgetContents)
        input_init_scrollarea.setWidget(self.gui.scrollAreaWidgetContents)

    def update_init_form(self):
       
        self.create_gridlayout()

        # Build input dict modification form
        input_grid_layout = self.gui.input_dict_gridlayout

        if not self.valid_init_dict:
            label = QLabel("No INIT_DICT found.")
            input_grid_layout.addWidget(label, 0, 0)
        else:

            try:
                for i,  (variable_name, entry_dict) in enumerate(self.init_dict.items()):
                    for labelname, default_value in entry_dict.items():
                        label = QLabel(str(labelname))
                        value_entry =  QLineEdit(str(default_value))
                        input_grid_layout.addWidget(label, i, 0)
                        input_grid_layout.addWidget(value_entry, i, 1)
            except AttributeError:
                label = QLabel("INIT_DICT found, but structure not valid.")
                input_grid_layout.addWidget(label, 0, 0)
                self.valid_init_dict = False


    def load_input_dict(self):
        """ Load input dict from Gridlayout in GUI"""

        if self.valid_init_dict:
            # load input dict
            input_grid_layout = self.gui.input_dict_gridlayout
            input_scrollarea = self.gui.scrollAreaWidgetContents

            num_cols = input_grid_layout.columnCount()
            num_rows = input_grid_layout.rowCount()
            init_widgets = input_scrollarea.children()[1:] # omitting first one since it's the gridlayout 

            assert len(init_widgets) == num_cols * num_rows

            reconstructed_init_dict = {}    

            for i in range(num_rows):
                reconstructed_init_dict[init_widgets[i*2].text()] = float(init_widgets[i*2+ 1].text())

            # reconstructed_init_dict is of form {"labelname" : "value"}
            # Now need to match it to the variable names:
            input_init_dict = self.init_dict # Is of form {"varname" : {"labelname" : "value"}}

            new_input_dict = self.init_dict.copy()

            for varname, entry_dict in new_input_dict.items():
                for labelname, _ in entry_dict.items():
                    new_input_dict[varname] = {labelname : reconstructed_init_dict[labelname]}

            # Commit input dict to parent dataset
            self.dataset.set_input_dict(new_input_dict)
        else:
            pass


    def configure(self):
        """ Configures the currently selected experiment + dataset """

        # If the experiment is running, do nothing
        try:
            if self.experiment_thread.isRunning():
                self.log.warn('Did not configure experiment, since it '
                              'is still in progress')
                return
        except:
            pass


        if not self.valid_init_dict:
            self.log.warn("No valid INIT_DICT found.")

        # Load the config
        self.reload_config()

        # Load experiment module
        self.module = importlib.import_module(self.exp_name)
        self.module = importlib.reload(self.module)

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
        # If we're not setting up a new measurement type, just clear the data

        # We are reading in the required base-dataset by looking at the define_dataset() as defined in the experiment script.
        try:
            classname = self.module.define_dataset()
        except AttributeError:
            error_msg = "No 'define_dataset' method found in experiment script."
            self.log.error("No 'define_dataset' method found in experiment script.")
            return

        try:
            self.dataset = getattr(datasets, classname)(
                gui=self.gui,
                log=self.log,
                config=self.config
            )
        except AttributeError:
            error_msg = f"Dataset name {classname} as provided in 'define_dataset' method in experiment script is not valid."
            self.log.error(error_msg)
            return

        # Load input dict from GUI so it is accessible for config function.
        self.load_input_dict()

        # Run any pre-experiment configuration
        try:
            self.module.configure(dataset=self.dataset, **self.clients)
        except AttributeError:
            pass
        self.experiment = self.module.experiment
    

        self.log.info(f'Experiment {self.exp_name} configured')
        self.gui.exp_preview.setStyleSheet('font: 10pt "Consolas"; '
                                           'color: rgb(255, 255, 255); '
                                           'background-color: rgb(50, 50, 50);')

    def clear_data(self):
        """ Clears all data from curves"""
        self.log.info("Clearing data")
        self.dataset.clear_all_data()

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

            # self.experiment_thread = ExperimentThread(
            #     self.experiment,
            #     dataset=self.dataset,
            #     gui=self.gui,
            #     **self.clients
            # )

            #
            self.experiment_thread = QtCore.QThread()
            self.experiment_worker = ExperimentWorker(
                self.experiment,
                dataset=self.dataset,
                gui=self.gui,
                **self.clients
            )
            self.experiment_worker.moveToThread(self.experiment_thread)
            self.experiment_thread.started.connect(self.experiment_worker.run)
            self.experiment_worker.finished.connect(self.experiment_thread.quit)
            self.experiment_thread.finished.connect(self.stop)
            self.experiment_worker.finished.connect(self.experiment_worker.deleteLater)
            self.experiment_thread.finished.connect(self.experiment_thread.deleteLater)
            self.experiment_worker.status_flag.connect(self.dataset.interpret_status)

            self.experiment_thread.start()
            #

            # self.experiment_thread.status_flag.connect(self.dataset.interpret_status)
            # self.experiment_thread.finished.connect(self.stop)
            self.log.update_metadata(
                exp_start_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S:%f')
            )

        # Stop experiment
        else:
            # self.experiment_thread.running = False
            self.experiment_worker.running = False

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


class ExperimentWorker(QtCore.QObject):
    """ Worker for Thread that simply runs the experiment repeatedly """

    # Flag to monitor whether experiment alarm goes off
    status_flag = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, experiment, **params):
        self.experiment = experiment
        self.params = params
        self.running = True
        super().__init__()
        # self.start()

    def run(self):
        self.params['iter_num'] = 0
        while self.running:
            self.experiment(
                thread=self,
                status_flag=self.status_flag,
                **self.params)
            self.params['iter_num'] += 1

        self.finished.emit()
        return


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
    control = DataTaker(config='preselected_histogram')
    control.gui.app.exec_()


def launch(**kwargs):

    config = load_script_config(
        script='data_taker',
        config=kwargs['config'],
        logger=kwargs['logger']
    )

    # Instantiate Monitor script
    control = DataTaker(
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
