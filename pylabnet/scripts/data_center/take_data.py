""" Module for taking data using arbitrary experiment scripts
    and Dataset objects """

import socket
import os
import sys
import inspect
import importlib
import time
from PyQt5 import QtWidgets, QtGui, QtCore

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import load_config
from pylabnet.scripts.data_center import datasets


REFRESH_RATE = 10    # refresh rate in ms

class DataTaker:

    def __init__(self, logger=None, clients={}, config=None):

        self.log = LogHandler(logger)
        
        # Instantiate GUI window
        self.gui = Window(
            gui_template='data_taker', 
            host=socket.gethostbyname(socket.gethostname())
        )

        # Configure list of experiments
        self.gui.config.setText(config)
        self.config = load_config(config, logger=self.log)
        self.exp_path = self.config['exp_path']
        if self.exp_path is None:
            self.exp_path = os.getcwd()
        sys.path.insert(1, self.exp_path)
        self.update_experiment_list()

        # Configure list of clients
        self.clients = clients
        for client_name, client_obj in self.clients.items():
            client_item = QtWidgets.QListWidgetItem(client_name)
            client_item.setToolTip(str(client_obj))
            self.clients.addItem(client_item)

        # Configure dataset menu
        for name, obj in inspect.getmembers(datasets):
            if inspect.isclass(obj) and issubclass(obj, datasets.Dataset):
                self.gui.dataset.addItem(name)

        # Configure button clicks
        self.gui.configure.clicked.connect(self.configure)
        self.gui.run.clicked.connect(self.run)
        
    def update_experiment_list(self):
        """ Updates list of experiments """

        self.gui.exp.clear()
        for filename in os.listdir(self.exp_path):
            if filename.endswith('.py'):
                self.gui.exp.addItem(filename[:-3])
        self.gui.exp.itemClicked.connect(self.display_experiment)

    def display_experiment(self, item):
        """ Displays the currently clicked experiment in the text browser

        :param item: (QlistWidgetItem) with label of name of experiment to display
        """

        with open(os.path.join(self.exp_path, f'{item.text()}.py'), 'r') as exp_file:
            exp_content = exp_file.read()

        self.gui.exp_preview.setText(exp_content)
        self.gui.exp_preview.setStyleSheet('font: 12pt "Consolas"; '
                                           'color: rgb(255, 255, 255); '
                                           'background-color: rgb(0, 0, 0);')

    def configure(self):
        """ Configures the currently selected experiment + dataset """

        # Set all experiments to normal state and highlight configured expt
        for item_no in range(self.gui.exp.count()):
            self.gui.exp.item(item_no).setBackground(QtGui.QBrush(QtGui.QColor('black')))
        self.gui.exp.currentItem().setBackground(QtGui.QBrush(QtGui.QColor('darkRed')))
        exp_name = self.gui.exp.currentItem().text()
        self.module = importlib.import_module(exp_name)
        self.module = importlib.reload(self.module)

        # Run any pre-experiment configuration
        try:
            self.module.configure(**self.clients)
        except AttributeError:
            pass
        self.experiment = self.module.experiment

        self.log.info(f'Experiment {exp_name} configured')
        self.gui.exp_preview.setStyleSheet('font: 12pt "Consolas"; '
                                           'color: rgb(255, 255, 255); '
                                           'background-color: rgb(50, 50, 50);')

        # Clear graph area and set up dataset
        for index in reversed(range(self.gui.graph_layout.count())):
            self.gui.graph_layout.itemAt(index).widget().deleteLater()
        self.dataset = getattr(datasets, self.gui.dataset.currentText())(
            gui=self.gui
        )

    def run(self):
        """ Runs/stops the experiment """

        # Run experiment
        if self.gui.run.text() == 'Run':
            self.gui.run.setStyleSheet('background-color: red')
            self.gui.run.setText('Stop')
            self.log.info('Experiment started')

            self.experiment_thread = ExperimentThread(
                self.experiment,
                dataset=self.dataset,
                gui=self.gui,
                **self.clients
            )
            self.update_thread = UpdateThread(
                dataset=self.dataset
            )
            self.experiment_thread.finished.connect(self.run)

        # Stop experiment
        else:
            self.gui.run.setStyleSheet('background-color: green')
            self.gui.run.setText('Run')
            self.log.info('Experiment stopped')
            self.experiment_thread.running = False
            self.update_thread.running = False


class ExperimentThread(QtCore.QThread):

    def __init__(self, experiment, **params):
        self.experiment = experiment
        self.params = params
        self.running = True
        super().__init__()
        self.start()
    
    def run(self):
        while self.running:
            self.experiment(**self.params)

class UpdateThread(QtCore.QThread):

    def __init__(self, dataset):
        self.dataset = dataset
        self.running = True
        super().__init__()
        self.start()
    
    def run(self):
        while self.running:
            self.dataset.update()
            self.msleep(REFRESH_RATE)




def main():
    control = DataTaker(config='laser_scan')
    control.gui.app.exec_()

if __name__== '__main__':
    main()
