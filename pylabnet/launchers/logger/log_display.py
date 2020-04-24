""" Launches the logger + graphical display """

import sys
import socket
import os
import time
import subprocess
from io import StringIO
from pylabnet.utils.logging.logger import LogService
from pylabnet.core.generic_server import GenericServer
from PyQt5 import QtWidgets, QtGui, QtCore
from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient
from pylabnet.utils.helper_methods import dict_to_str, remove_spaces
import pickle


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class Controller:
    """ Class for log system controller """

    LOGGER_UI = 'logger'
    LOG_PORT = 1234
    GUI_PORT = 5678
    GUI_NAME = 'logger_GUI'

    def __init__(self, *args, **kwargs):

        self.log_service = None
        self.log_server = None
        self.gui_logger = None
        self.gui_service = None
        self.gui_server = None
        self.client_list = {}
        self.port_list = {}
        self.script_list = {}
        self.disconnection = False
        self.current_output = ''

        sys.stdout = StringIO()

        # Instantiate GUI application
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = Window(self.app, gui_template=self.LOGGER_UI)

        self._start_logger()
        self._initialize_gui()

    def start_gui_server(self, gui_port=None):

        # Assign the port to use
        if gui_port is None:
            gui_port = self.GUI_PORT

        # Try to connect to the logger
        try:
            self.gui_logger = LogClient(
                host='localhost',
                port=self.LOG_PORT,
                module_tag=self.GUI_NAME,
                server_port=gui_port,
                ui=self.LOGGER_UI
            )
        except ConnectionRefusedError:
            raise

        # Instantiate GUI server and update GUI with port details
        self.gui_service = Service()
        self.gui_service.assign_module(module=self.main_window)
        self.gui_service.assign_logger(logger=self.gui_logger)
        self.gui_server = GenericServer(
            service=self.gui_service,
            host='localhost',
            port=gui_port
        )
        self.gui_server.start()
        self.main_window.gui_label.setText('GUI Port: {}'.format(gui_port))

        # Update internal attributes and add to list of log clients
        self.client_list[self.GUI_NAME] = QtWidgets.QListWidgetItem(self.GUI_NAME)
        self.port_list[self.GUI_NAME] = [port for port in self.log_server._server.clients][0]
        self.main_window.client_list.addItem(self.client_list[self.GUI_NAME])
        self.client_list[self.GUI_NAME].setToolTip(dict_to_str(self.log_service.client_data[self.GUI_NAME]))

    def update_terminal(self):
        """ Updates terminal output on GUI """

        self.main_window.terminal.append(sys.stdout.getvalue())
        try:
            self.main_window.terminal.moveCursor(QtGui.QTextCursor.End)
        except TypeError:
            pass
        sys.stdout.truncate(0)
        sys.stdout.seek(0)

    def check_disconnection(self):
        """ Checks if a client has disconnected and raises a flag if so"""

        if 'Client disconnected' in sys.stdout.getvalue() or self.disconnection:
            self.disconnection = True

    def disconnect(self):
        """ Handles case where client has disconnected """

        to_del = [client for (client, port) in self.port_list.items() if port not in self.log_server._server.clients]
        for client in to_del:
            print('[INFO] {} disconnected at {}'.format(client, time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())))
            self.main_window.client_list.takeItem(self.main_window.client_list.row(self.client_list[client]))
            del self.client_list[client]
            del self.port_list[client]
            del self.log_service.client_data[client]
            self.disconnection = False

    def update_connection(self):
        """ Checks if new/updated connections have been made and updates accordingly"""

        # Figure out ports/clients to add
        port_to_add = [port for port in self.log_server._server.clients if port not in self.port_list.values()]
        client_to_add = [client for client in self.log_service.client_data if client not in self.client_list]

        # Add client and update relevant directories + GUI
        if len(client_to_add) > 0:
            client = client_to_add[0]
            self.client_list[client] = QtWidgets.QListWidgetItem(client)
            self.main_window.client_list.addItem(self.client_list[client])
            try:
                self.main_window.client_list.moveCursor(QtGui.QTextCursor.End)
            except TypeError:
                pass
            self.client_list[client].setToolTip(dict_to_str(self.log_service.client_data[client]))
            if len(port_to_add) > 0:
                self.port_list[client] = port_to_add[0]

        # Check for updates to client data
        while len(self.log_service.data_updated) > 0:
            self.client_list[self.log_service.data_updated[0]].setToolTip(
                dict_to_str(self.log_service.client_data[self.log_service.data_updated[0]])
            )
            del self.log_service.data_updated[0]

    def _configure_clicks(self):
        """ Configures what to do if script is clicked """

        self.main_window.script_list.itemDoubleClicked.connect(self._clicked)

    def _clicked(self):
        script_to_run = list(self.script_list.keys())[list(self.script_list.values()).index(
            self.main_window.script_list.currentItem()
        )]
        launch_time = time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
        print('Launching {} at {}'.format(script_to_run, launch_time))

        # Build the bash command to input all active servers and relevant port numbers to script
        bash_cmd = 'start /min "{}, {}" /wait {} {} --logport {} --numclients {}'.format(
            script_to_run, 
            launch_time,
            sys.executable,
            os.path.join(os.path.dirname(os.path.realpath(__file__)),script_to_run), 
            self.LOG_PORT, 
            len(self.client_list)
        )
        client_index = 1
        for client in self.client_list:
            bash_cmd += ' --client{} {} --ip{} {}'.format(
                client_index, remove_spaces(client), client_index, self.log_service.client_data[client]['ip']
            )

            # Add port of client's server, if applicable
            if 'port' in self.log_service.client_data[client]:
                bash_cmd += ' --port{} {}'.format(client_index, self.log_service.client_data[client]['port'])

            # If this client has relevant .ui file, pass this info
            if 'ui' in self.log_service.client_data[client]:
                bash_cmd += ' --ui{} {}'.format(client_index, self.log_service.client_data[client]['ui'])

            client_index += 1

        # Launch the new process
        subprocess.Popen(bash_cmd, shell=True)

    def _start_logger(self):
        """ Starts the log server """

        self.log_service = LogService()
        self.log_server = GenericServer(service=self.log_service, host='localhost', port=self.LOG_PORT)
        self.log_server.start()

    def _initialize_gui(self):
        """ Initializes basic GUI display """

        self.main_window.ip_label.setText('IP Address: {}'.format(socket.gethostbyname(socket.gethostname())))
        self.main_window.logger_label.setText('Logger Port: {}'.format(self.LOG_PORT))
        self.main_window.terminal.setText('Log messages will be displayed below \n')

        # Configure list of scripts to run and clicking actions
        self._load_scripts()
        self._configure_clicks()

        self.main_window.force_update()

    def _load_scripts(self):
        """ Loads all scripts from current working directory """

        # Get all relevant files
        current_directory = os.path.dirname(os.path.realpath(__file__))
        files = [file for file in os.listdir(current_directory) if (
            os.path.isfile(os.path.join(
                current_directory, file
            )) and '__init__.py' not in file and 'log_display.py' not in file
        )]

        for file in files:
            self.script_list[file] = QtWidgets.QListWidgetItem(file)
            self.main_window.script_list.addItem(self.script_list[file])


def main():
    """ Runs the log display """

    log_controller = Controller()
    log_controller.start_gui_server()
    while not log_controller.main_window.stop_button.isChecked():

        # Handle external configuration
        log_controller.main_window.configure_widgets()
        log_controller.main_window.update_widgets()

        # New terminal input
        if sys.stdout.getvalue() is not '':

            # Check for disconnection events
            log_controller.check_disconnection()

            # Handle new connections
            log_controller.update_connection()

            # Update terminal
            log_controller.update_terminal()

        # Handle disconnection events
        if log_controller.disconnection:
            log_controller.disconnect()

        # Update display
        log_controller.main_window.force_update()

    # Exit app (does not close servers)
    sys.exit(log_controller.app.exec_())


if __name__ == '__main__':
    main()
