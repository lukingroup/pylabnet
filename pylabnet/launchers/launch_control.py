""" Initializes the logger + graphical display for launching pylabnet scripts """

import sys
import socket
import os
import time
import subprocess
from io import StringIO
import copy
import ctypes
import re
from pylabnet.utils.logging.logger import LogService
from PyQt5 import QtWidgets, QtGui, QtCore
from datetime import datetime

from pylabnet.utils.logging.logger import LogService
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.network.client_server.external_gui import Service, Client
from pylabnet.utils.logging.logger import LogClient
from pylabnet.utils.helper_methods import dict_to_str, remove_spaces, create_server, show_console, hide_console, get_dated_subdirectory_filepath


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class LaunchWindow(Window):
    """ Child class of GUI Window enabling killing of all servers """

    def __init__(self, app, controller, gui_template=None, run=True):
        """ Instantiates LaunchWindow

        :param app: GUI application
        :param controller: Controller object
        :param gui_template: (str) name of .ui file to use
        :param run: whether or not to run GUI on instantiation
        """

        super().__init__(app, gui_template=gui_template)
        self.controller = controller

    def closeEvent(self, event):
        """ Occurs when window is closed. Overwrites parent class method"""

        self.controller.kill_servers()
        self.stop_button.setChecked(True)

class Controller:
    """ Class for log system controller """

    LOGGER_UI = 'logger_remote'
    GUI_NAME = 'logger_GUI'

    # When kept as None, random port numbers will be used
    # use these values to override and set manual port numbers if desired
    LOG_PORT = None
    GUI_PORT = None

    def __init__(self, proxy=False):
        """ Initializes launch control GUI """

        self.log_service = None
        self.log_server = None
        self.gui_client = None
        self.gui_logger = None
        self.gui_service = None
        self.log_port = self.LOG_PORT
        self.gui_port = self.GUI_PORT
        self.gui_server = None
        self.client_list = {}
        self.port_list = {}
        self.script_list = {}
        self.client_data = {}
        self.disconnection = False
        self.debug = False
        self.debug_level = None
        try:
            if sys.argv[1] == '-p' or proxy:
                self.proxy = True
            else:
                self.proxy = False
        except IndexError:
            if proxy:
                self.proxy = True
            else:
                self.proxy = False
        self.host = socket.gethostbyname(socket.gethostname())
        self.update_index = 0

        # Find logger if applicable
        if self.proxy:
            try:
                self.host = sys.argv[2]
            except IndexError:
                show_console()
                self.host = input('Please enter the master Launch Control IP address:\n>> ')
            show_console()
            self.log_port = int(input('Please enter the master Logger Port:\n>> '))
            self.gui_port = int(input('Please enter the master GUI Port:\n>> '))
            hide_console()

        sys.stdout = StringIO()

        # Instantiate GUI application
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setWindowIcon(
            QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
        )
        self.main_window = LaunchWindow(self.app, self, gui_template=self.LOGGER_UI)

    def start_gui_server(self):
        """ Starts the launch controller GUI server, or connects to the server and updates GUI"""

        module_str = ''
        if self.proxy:
            module_str = '_proxy'
        # connect to the logger
        self.gui_logger = LogClient(
            host=self.host,
            port=self.log_port,
            module_tag=self.GUI_NAME+module_str,
            ui=self.LOGGER_UI
        )

        gui_str = ''
        if self.proxy:
            gui_str = 'Master '

            # Connect to the GUI server
            try:
                self.gui_client = Client(host=self.host, port=self.gui_port)
            except ConnectionRefusedError:
                self.gui_logger.error(f'Failed to connect to GUI Server with IP address: {self.host}, '
                                      f'Port: {self:gui_port}')
                raise

            # Now update GUI to mirror clients
            self._copy_master()

            # Get the latest update index
            buffer = self.gui_client.get_text('buffer')
            self.update_index = int(re.findall(r'\d+', re.findall(r'!~\d+~!', buffer)[-1])[0])

        else:
            # Instantiate GUI server and update GUI with port details
            self.gui_service = Service()
            self.gui_service.assign_module(module=self.main_window)
            self.gui_service.assign_logger(logger=self.gui_logger)
            if self.gui_port is None:
                self.gui_server, self.gui_port = create_server(
                    self.gui_service,
                    logger=self.gui_logger,
                    host=socket.gethostbyname(socket.gethostname())
                    )
            else:
                try:
                    self.gui_server = GenericServer(
                        service=self.gui_service,
                        host='localhost',
                        port=self.gui_port
                    )
                except ConnectionRefusedError:
                    self.gui_logger.error(f'Failed to instantiate GUI Server at port {self.gui_port}')
                    raise
            self.gui_server.start()
            self.gui_logger.update_data(data=dict(port=self.gui_port))
            # Update internal attributes and add to list of log clients
            self.client_list[self.GUI_NAME] = QtWidgets.QListWidgetItem(self.GUI_NAME)
            self.port_list[self.GUI_NAME] = [port for port in self.log_server._server.clients][0]
            self.main_window.client_list.addItem(self.client_list[self.GUI_NAME])
            self.client_list[self.GUI_NAME].setToolTip(dict_to_str(self.log_service.client_data[self.GUI_NAME]))
            self.client_data[self.GUI_NAME+module_str] = self.log_service.client_data[self.GUI_NAME]

        self.main_window.gui_label.setText('{} GUI Port: {}'.format(gui_str, self.gui_port))

    def update_terminal(self):
        """ Updates terminal output on GUI """

        to_append = sys.stdout.getvalue()
        self.main_window.terminal.append(to_append)
        self.main_window.buffer_terminal.append(to_append)
        try:
            self.main_window.terminal.moveCursor(QtGui.QTextCursor.End)
        except TypeError:
            pass
        sys.stdout.truncate(0)
        sys.stdout.seek(0)

        # Update buffer terminal
        buffer_str = f'!~{self.update_index}~!{to_append}'
        self.main_window.buffer_terminal.append(buffer_str)
        self.update_index += 1

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
            del self.client_data[client]
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
            self.client_data[client] = self.log_service.client_data[client]

        # Check for updates to client data
        while len(self.log_service.data_updated) > 0:
            self.client_list[self.log_service.data_updated[0]].setToolTip(
                dict_to_str(self.log_service.client_data[self.log_service.data_updated[0]])
            )
            del self.log_service.data_updated[0]

    def start_logger(self):
        """ Starts the log server """

        self.log_service = LogService()
        if self.LOG_PORT is None:
            self.log_server, self.log_port = create_server(
                self.log_service,
                host=socket.gethostbyname(socket.gethostname())
                )
        else:
            try:
                self.log_server = GenericServer(
                    service=self.log_service,
                    host=socket.gethostname(socket.gethostname()),
                    port=self.LOG_PORT
                    )
            except ConnectionRefusedError:
                print(f'Failed to insantiate Log Server at port {self.LOG_PORT}')
                raise
        self.log_server.start()

    def initialize_gui(self):
        """ Initializes basic GUI display """

        # sys.stdout = StringIO()
        # self.app = QtWidgets.QApplication(sys.argv)
        # self.main_window = Window(self.app, gui_template=self.LOGGER_UI)

        ip_str, ip_str_2, log_str = '', '', ''
        if self.proxy:
            self.main_window.setWindowTitle('Launch Control (Proxy)')
            ip_str = 'Master (Local) '
            ip_str_2 = f' ({socket.gethostbyname(socket.gethostname())})'
            log_str = 'Master '
        self.main_window.ip_label.setText(
            f'{ip_str}IP Address: {self.host}'+ip_str_2
            )
        self.main_window.logger_label.setText(f'{log_str} Logger Port: {self.log_port}')

        if self.proxy:
            self.main_window.terminal.setText('Connected to master Log Server. \n')
        self.main_window.terminal.setText('Log messages will be displayed below \n')
        self.main_window.buffer_terminal.document().setMaximumBlockCount(100)

        # Assign widgets for remote access
        self.main_window.assign_container('client_list', 'clients')
        self.main_window.assign_label('buffer_terminal', 'buffer')
        self.main_window.assign_event_button('debug_radio_button', 'debug')

        # Hide some buttons
        self.main_window.file_viewer.setHidden(True)
        self.main_window.logfile_status_button.setHidden(True)
        self.main_window.debug_label.setHidden(True)
        self.main_window.debug_comboBox.setHidden(True)
        self.main_window.logfile_status_button.setHidden(True)
        self.main_window.log_previous.setHidden(True)
        self.main_window.logfile_status_indicator.setEnabled(False)

        # Configure list of scripts to run and clicking actions
        self._load_scripts()
        self._configure_clicks()
        self._configure_debug()
        self._configure_debug_combo_select()
        self._configure_logfile()
        self._configure_logging()

        self.main_window.force_update()

    def update_proxy(self):
        """ Updates the proxy with new content using the buffer terminal"""

        # Check clients and update
        self._pull_connections()

        # Get buffer terminal
        buffer_terminal = self.gui_client.get_text('buffer')

        # Parse buffer terminal to get part of the message that is new
        new_msg = buffer_terminal[buffer_terminal.rfind(f'!~{self.update_index+1}~!'):-1]

        # Check if this failed
        if new_msg == '':

            # Check if the buffer is ahead of our last update
            up_str = re.findall(r'!~\d+~!', new_msg)
            if len(up_str) > 0:
                up_in = int(re.findall(r'\d+', up_str[0]))
                if up_in > self.update_index:
                    new_msg = buffer_terminal

        # If we have a new message to add, add it
        if new_msg != '':

            self.main_window.terminal.append(re.sub(r'!~\d+~!', '', new_msg))
            try:
                self.main_window.terminal.moveCursor(QtGui.QTextCursor.End)
            except TypeError:
                pass
            self.update_index = int(re.findall(r'\d+', re.findall(r'!~\d+~!', new_msg)[-1])[0])

    def kill_servers(self):
        """ Kills all servers connected to the logger, including the Log GUI and Log Server"""

        client_data = copy.deepcopy(self.client_data)
        del client_data['logger_GUI']
        for server_data in client_data:
            if 'port' in server_data:
                stop_client = ClientBase(host=server_data['ip'], port=server_data['port'])
                stop_client.close_server()
        self.gui_server.stop()
        self.log_server.stop()
        self.gui_logger.info(f'{self.client_data.pop("logger_GUI")}')
    
    def _configure_clicks(self):
        """ Configures what to do upon clicks """

        self.main_window.script_list.itemDoubleClicked.connect(self._clicked)
        self.main_window.close_server.pressed.connect(self._stop_server)

    def _stop_server(self):
        """ Stops the highlighted server, if applicable """

        client_to_stop = self.main_window.client_list.currentItem().text()
        server_data = self.client_data[client_to_stop]
        if 'port' in server_data:
            try:
                stop_client = ClientBase(host=server_data['ip'], port=server_data['port'])
                stop_client.close_server()
            except:
                self.gui_logger.warn(
                    f'Failed to shutdown server {client_to_stop}'
                    f'on host: {server_data["ip"]}, port: {server_data["port"]}'
                )
        else:
            self.gui_logger.warn(f'No server to shutdown for client {client_to_stop}')
    
    def _clicked(self):
        """ Launches the script that has been double-clicked

        Opens a new commandline subprocess using subprocess.Popen(bash_cmd) which runs the
        relevant python script, passing all relevant LogClient information via the commandline
        """

        script_to_run = list(self.script_list.keys())[list(self.script_list.values()).index(
            self.main_window.script_list.currentItem()
        )]
        launch_time = time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
        print('Launching {} at {}'.format(script_to_run, launch_time))  # TODO MAKE A LOG STATEMENT

        # Read debug state and set flag value accordingly.

        # Initial configurations: All flags down.
        debug_flag, server_debug_flag, gui_debug_flag = '0', '0', '0'

        # Raise flags if selected in combobox
        if self.debug:
            if self.debug_level == "launcher":
                debug_flag = '1'
            elif self.debug_level == "pylabnet_server":
                server_debug_flag = '1'
            elif self.debug_level == "pylabnet_gui":
                gui_debug_flag = '1'

        # Build the bash command to input all active servers and relevant port numbers to script
        # bash_cmd = 'start /min "{}, {}" /wait "{}" "{}" --logip {} --logport {} --numclients {} --debug {} --server_debug {} --gui_debug {}'.format(
        #     script_to_run,
        #     launch_time,
        #     sys.executable,
        #     os.path.join(os.path.dirname(os.path.realpath(__file__)), script_to_run),
        #     self.host,
        #     self.log_port,
        #     len(self.client_list),
        #     debug_flag,
        #     server_debug_flag,
        #     gui_debug_flag
        # )
        bash_cmd = 'start "{}, {}" "{}" "{}" --logip {} --logport {} --numclients {} --debug {} --server_debug {} --gui_debug {}'.format(
            script_to_run,
            launch_time,
            sys.executable,
            os.path.join(os.path.dirname(os.path.realpath(__file__)), script_to_run),
            self.host,
            self.log_port,
            len(self.client_list),
            debug_flag,
            server_debug_flag,
            gui_debug_flag
        )
        client_index = 1
        for client in self.client_list:
            bash_cmd += ' --client{} {} --ip{} {}'.format(
                client_index, remove_spaces(client), client_index, self.client_data[client]['ip']
            )

            # Add port of client's server, if applicable
            if 'port' in self.client_data[client]:
                bash_cmd += ' --port{} {}'.format(client_index, self.client_data[client]['port'])

            # If this client has relevant .ui file, pass this info
            if 'ui' in self.client_data[client]:
                bash_cmd += ' --ui{} {}'.format(client_index, self.client_data[client]['ui'])

            client_index += 1

        # Launch the new process
        subprocess.Popen(bash_cmd, shell=True)

    def _load_scripts(self):
        """ Loads all relevant scripts from current working directory """

        # Get all relevant files
        current_directory = os.path.dirname(os.path.realpath(__file__))
        files = [file for file in os.listdir(current_directory) if (
            os.path.isfile(os.path.join(
                current_directory, file
            )) and '.py' in file and '__init__.py' not in file and 'launch_control.py' not in file and 'launcher.py' not in file
        )]

        for file in files:
            self.script_list[file] = QtWidgets.QListWidgetItem(file.split('.')[0])
            self.main_window.script_list.addItem(self.script_list[file])

    def _copy_master(self):
        """ Updates the GUI to copy the GUI of the master GUI server """

        # Get a dictionary of all client names and tooltip info
        clients = self.gui_client.get_container_info('clients')

        # Update the proxy GUI to reflect the client list of the main GUI
        for client, info in clients.items():
            self.client_list[client] = QtWidgets.QListWidgetItem(client)
            self.main_window.client_list.addItem(self.client_list[client])
            self.client_list[client].setToolTip(info)

            # Add client data
            self.client_data[client] = {}
            if 'ip: ' in info:
                self.client_data[client]['ip'] = info.split('ip: ')[1].split('\n')[0]
            if 'timestamp: ' in info:
                self.client_data[client]['timestamp'] = info.split('timestamp: ')[1].split('\n')[0]
            if 'ui: ' in info:
                self.client_data[client]['ui'] = info.split('ui: ')[1].split('\n')[0]
            if 'port: ' in info:
                self.client_data[client]['port'] = info.split('port: ')[1].split('\n')[0]

    def _pull_connections(self):
        """ Updates the proxy's client list """

        # Get a dictionary of all client names and tooltip info
        clients = self.gui_client.get_container_info('clients')

        # Update the proxy GUI to reflect the client list of the main GUI
        add_clients = list(set(clients.keys()) - set(self.client_list.keys()))
        remove_clients = list(set(self.client_list.keys()) - set(clients.keys()))
        other_clients = list(set(clients.keys()) - set(add_clients) - set(remove_clients))

        # Add clients
        for client in add_clients:
            self.client_list[client] = QtWidgets.QListWidgetItem(client)
            self.main_window.client_list.addItem(self.client_list[client])
            self.client_list[client].setToolTip(clients[client])

            # Add client data
            self.client_data[client] = {}
            print('Client: '+client)
            if 'ip: ' in clients[client]:
                self.client_data[client]['ip'] = clients[client].split('ip: ')[1].split('\n')[0]
            if 'timestamp: ' in clients[client]:
                self.client_data[client]['timestamp'] = clients[client].split('timestamp: ')[1].split('\n')[0]
            if 'ui: ' in clients[client]:
                self.client_data[client]['ui'] = clients[client].split('ui: ')[1].split('\n')[0]
            if 'port: ' in clients[client]:
                self.client_data[client]['port'] = clients[client].split('port: ')[1].split('\n')[0]

        # Remove clients
        for client in remove_clients:
            self.main_window.client_list.takeItem(self.main_window.client_list.row(self.client_list[client]))
            del self.client_list[client]

        # Update any other changes
        for client in other_clients:
            if self.client_list[client].toolTip() != clients[client]:
                self.client_list[client].setToolTip(clients[client])
                if 'ip: ' in clients[client]:
                    self.client_data[client]['ip'] = clients[client].split('ip: ')[1].split('\n')[0]
                if 'timestamp: ' in clients[client]:
                    self.client_data[client]['timestamp'] = clients[client].split('timestamp: ')[1].split('\n')[0]
                if 'ui: ' in clients[client]:
                    self.client_data[client]['ui'] = clients[client].split('ui: ')[1].split('\n')[0]
                if 'port: ' in clients[client]:
                    self.client_data[client]['port'] = clients[client].split('port: ')[1].split('\n')[0]


    # Defines what to do if debug radio button is clicked.
    def _configure_debug(self):
        self.main_window.debug_radio_button.toggled.connect(self._update_debug_settings)

    def _configure_logging(self):
        """ Defines what to do if the Start/Stop Logging button is clicked """
        self.main_window.logfile_status_button.toggled.connect(self._start_stop_logging)

    def _configure_logfile(self):
        """ Defines what to do if the logfile radio button is clicked """
        self.main_window.log_file_button.toggled.connect(self._update_logfile_status)
    
    # Defines what to do if combobox is changed.
    def _configure_debug_combo_select(self):
        self.main_window.debug_comboBox.currentIndexChanged.connect(self._update_debug_level)

    def _update_debug_settings(self):
        if self.main_window.debug_radio_button.isChecked():
            self.debug = True

            # Enable and show combobox.
            self.main_window.debug_comboBox.setEnabled(True)
            self.main_window.debug_label.setHidden(False)
            self.main_window.debug_comboBox.setHidden(False)

        else:
            self.debug = False
            # Disable and hide combobox.
            self.main_window.debug_comboBox.setEnabled(False)
            self.main_window.debug_label.setHidden(True)
            self.main_window.debug_comboBox.setHidden(True)

        # Update debug level.
        self._update_debug_level()

    def _update_logfile_status(self):
        """ Updates the status of whether or not we are using a logfile """
        if self.main_window.log_file_button.isChecked():
            
            # Enable and show file browser
            self.main_window.file_viewer.setEnabled(True)
            self.main_window.file_viewer.setHidden(False)
            self.main_window.logfile_status_button.setEnabled(True)
            self.main_window.logfile_status_button.setHidden(False)
            self.main_window.log_previous.setEnabled(True)
            self.main_window.log_previous.setHidden(False)
            
            # Assign a file system model if we're not already logging
            if not self.main_window.logfile_status_button.isChecked():
                model = QtWidgets.QFileSystemModel()
                model.setRootPath(QtCore.QDir.rootPath())
                self.main_window.file_viewer.setModel(model)
                self.main_window.file_viewer.setRootIndex(model.index(QtCore.QDir.homePath()))
                self.main_window.file_viewer.setColumnWidth(0, 200)

        else:

            # Disable and hide file browser
            self.main_window.file_viewer.setHidden(True)
            self.main_window.file_viewer.setEnabled(False)
            self.main_window.logfile_status_button.setHidden(True)
            self.main_window.logfile_status_button.setEnabled(False)
            self.main_window.log_previous.setEnabled(False)
            self.main_window.log_previous.setHidden(True)

    def _update_debug_level(self, i=0):
        # Set debug level according to combo-box selection.
        # Levels are:
        # pylabnet_server, pylabnet_gui, launcher
        self.debug_level = self.main_window.debug_comboBox.currentText()

    def _start_stop_logging(self):
        """ Starts or stops logging to file depending on situation """

        if self.main_window.logfile_status_button.isChecked():

            # Actually start logging
            filename = f'logfile_{datetime.now().strftime("%H_%M_%S")}'
            try:
                filepath = self.main_window.file_viewer.model().filePath(
                    self.main_window.file_viewer.selectionModel().currentIndex()
                )
                self.log_service.add_logfile(
                    name=filename,
                    dir_path=filepath
                )
            except Exception as error_msg:
                print(f'Failed to start logging to file {os.path.join(filepath, filename)}.\n{error_msg}')

            # Change button color and text
            self.main_window.logfile_status_button.setStyleSheet("background-color: red")
            self.main_window.logfile_status_button.setText('Stop logging to file')
            self.main_window.logfile_status_indicator.setChecked(True)

            # Add previous text to logfile
            if self.main_window.log_previous.isChecked():
                self.log_service.logger.info(
                    f'Previous log terminal content: \n{self.main_window.terminal.toPlainText()}'
                    f'\n---------------------------'
                )

        else:

            # Change button color and text
            self.main_window.logfile_status_button.setStyleSheet("background-color: green")
            self.main_window.logfile_status_button.setText('Start logging to file')
            self.main_window.logfile_status_indicator.setChecked(False)

            # Actually stop logging
            self.log_service.stop_latest_logfile()


def main():
    """ Runs the launch controller """

    hide_console()
    log_controller = Controller()
    run(log_controller)

def main_proxy():
    """ Runs the launch controller overriding commandline arguments in proxy mode """

    log_controller = Controller(proxy=True)
    run(log_controller)

def run(log_controller):
    """ Runs the launch controller once a Controller is instantiated"""

    # Instantiate GUI
    if not log_controller.proxy:
        log_controller.start_logger()
    log_controller.initialize_gui()
    log_controller.start_gui_server()

    # Standard operation
    while not log_controller.main_window.stop_button.isChecked():

        # For proxy launch controller, just check main GUI for updates
        if log_controller.proxy:
            log_controller.update_proxy()
        else:

            # Handle external configuration via GUI server
            log_controller.main_window.configure_widgets()
            log_controller.main_window.update_widgets()

            # New terminal input
            if sys.stdout.getvalue() != '':

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

    # Exit, close servers
    log_controller.kill_servers()
    log_controller.gui_server.stop()
    log_controller.log_server.stop()


if __name__ == '__main__':
    main()
