""" Initializes the logger + graphical display for launching pylabnet scripts """

import sys
import socket
import os
import time
from contextlib import closing
import subprocess
import platform
from io import StringIO
import copy
import ctypes
import re
from pylabnet.utils.logging.logger import LogService
from PyQt5 import QtWidgets, QtGui, QtCore
from datetime import datetime
from queue import Queue
import numpy as np

from pylabnet.utils.logging.logger import LogService
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window, ParameterPopup
from pylabnet.network.client_server.external_gui import Service, Client
from pylabnet.utils.logging.logger import LogClient
from pylabnet.launchers.launcher import Launcher
from pylabnet.utils.helper_methods import (UnsupportedOSException, get_os, dict_to_str, load_config,
    remove_spaces, create_server, hide_console, get_dated_subdirectory_filepath,
    get_config_directory, load_device_config, launch_device_server, launch_script, get_ip)

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
        self.apply_stylesheet()
        self.buffer_terminal.setVisible(False)

    def closeEvent(self, event):
        """ Occurs when window is closed. Overwrites parent class method"""

        if not self.controller.proxy:
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

    def __init__(self, proxy=False, master=False, staticproxy=False):
        """ Initializes launch control GUI """

        self.operating_system = get_os()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setWindowIcon(
            QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
        )
        # Instantiate GUI application
        if self.operating_system == 'Windows':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')

        self.main_window = LaunchWindow(self.app, self, gui_template=self.LOGGER_UI)
        self.main_window.stop_button.clicked.connect(self._kill)
        if self.operating_system not in ['Linux', 'Windows']:
            raise UnsupportedOSException
        try:
            if sys.argv[1] == '-m' or master:
                self.master = True
            else:
                self.master = False
        except IndexError:
            if master:
                self.master = True
            else:
                self.master = False

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

        try:
            if sys.argv[1] == '-sp' or staticproxy:
                self.staticproxy = True
            else:
                self.staticproxy = False
        except IndexError:
            if staticproxy:
                self.staticproxy = True
            else:
                self.staticproxy = False

        self.host = get_ip()
        self.update_index = 0

        # Retrieve static port info.
        if self.master:
            try:
                static_proxy_dict = load_config('static_proxy')
            except:
                print('No config found named static_proxy.json')
                time.sleep(10)
                raise
            self.log_port = static_proxy_dict['master_log_port']
            self.gui_port = static_proxy_dict['master_gui_port']
            hide_console()
        elif self.proxy:
            popup = ParameterPopup(
                host=str,
                log_port=str,
                gui_port=str
            )
            self.waiting_flag = True
            popup.parameters.connect(self.fill_parameters)
            while self.waiting_flag:
                self.app.processEvents()
        elif self.staticproxy:
            try:
                static_proxy_dict = load_config('static_proxy')
            except:
                print('No config found named static_proxy.json')
                time.sleep(10)
                raise
            self.host = static_proxy_dict['master_ip']
            self.log_port = static_proxy_dict['master_log_port']
            self.gui_port = static_proxy_dict['master_gui_port']
            self.proxy = True
            hide_console()
        else:
            self.log_port = self.LOG_PORT
            self.gui_port = self.GUI_PORT

        self.log_service = None
        self.log_server = None
        self.gui_client = None
        self.gui_logger = None
        self.gui_service = None
        self.gui_server = None
        self.client_list = {}
        self.port_list = {}
        self.script_list = {}
        self.client_data = {}
        self.disconnection = False
        self.debug = False
        self.debug_level = None
        self.autoscroll_off = False
        # date string is None if not logging to file, and gives today's date if logging to file.
        # For day-chopping purposes
        self.date_str = None

    def fill_parameters(self, params):
        """ Called when parameters have been entered into a popup """

        self.host = params['host']
        self.log_port = params['log_port']
        self.gui_port = params['gui_port']
        self.waiting_flag = False

    def start_gui_server(self):
        """ Starts the launch controller GUI server, or connects to the server and updates GUI"""

        module_str = ''
        if self.proxy:
            module_str = '_proxy'
        # connect to the logger
        try:
            self.gui_logger = LogClient(
                host=self.host,
                port=self.log_port,
                module_tag=self.GUI_NAME+module_str,
                ui=self.LOGGER_UI
            )
        except ConnectionRefusedError:
            self.main_window.terminal.setText('Failed to connect to master. Shutting down')
            self.main_window.force_update()
            time.sleep(10)
            raise

        # Instantiate GUI server and update GUI with port details
        self.gui_service = Service()
        self.gui_service.assign_module(module=self.main_window)
        self.gui_service.assign_logger(logger=self.gui_logger)
        if self.gui_port is None:
            self.gui_server, self.gui_port = create_server(
                self.gui_service,
                logger=self.gui_logger,
                host=get_ip()
            )
            my_port = self.gui_port
            self.main_window.gui_label.setText(
                f'GUI Port: {my_port}'
            )
        elif self.proxy:
            self.gui_server, my_port = create_server(
                self.gui_service,
                logger=self.gui_logger,
                host=get_ip()
            )
            self.main_window.gui_label.setText(
                f'Master (Local) GUI Port: {self.gui_port} ({my_port})'
            )
        else:
            try:
                self.gui_server = GenericServer(
                    service=self.gui_service,
                    host=get_ip(),
                    port=self.gui_port
                )
                my_port = self.gui_port
                self.main_window.gui_label.setText(
                    f'GUI Port: {my_port}'
                )
            except ConnectionRefusedError:
                self.gui_logger.error(f'Failed to instantiate GUI Server at port {self.gui_port}')
                raise
        self.gui_server.start()
        self.gui_logger.update_data(data=dict(port=my_port))

        if self.proxy:
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
            try:
                self.update_index = int(re.findall(r'\d+', re.findall(r'!~\d+~!', buffer)[-1])[0])
            except IndexError:
                self.update_index = 0

            self.gui_service = Service()
            self.gui_service.assign_module(module=self.main_window)
            self.gui_service.assign_logger(logger=self.gui_logger)

        else:

            # Update internal attributes and add to list of log clients
            self.client_list[self.GUI_NAME] = QtWidgets.QListWidgetItem(self.GUI_NAME)
            self.port_list[self.GUI_NAME] = [port for port in self.log_server._server.clients][0]
            self.main_window.client_list.addItem(self.client_list[self.GUI_NAME])
            self.client_list[self.GUI_NAME].setToolTip(dict_to_str(self.log_service.client_data[self.GUI_NAME]))
            self.client_data[self.GUI_NAME+module_str] = self.log_service.client_data[self.GUI_NAME]

    def update_terminal(self, text):
        """ Updates terminal output on GUI """

        self.main_window.terminal.append(text)
        if not self.autoscroll_off:
            try:
                self.main_window.terminal.moveCursor(QtGui.QTextCursor.End)
            except TypeError:
                pass
        # Update buffer terminal
        buffer_str = f'!~{self.update_index}~!{text}'
        self.main_window.buffer_terminal.append(buffer_str)
        self.update_index += 1

    def check_disconnection(self, text):
        """ Checks if a client has disconnected and raises a flag if so"""

        if 'Client disconnected' in text or self.disconnection:
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
        if self.LOG_PORT is None and not self.master:
            self.log_server, self.log_port = create_server(
                self.log_service,
                host=get_ip()
                )
        else:
            try:
                self.log_server = GenericServer(
                    service=self.log_service,
                    host=get_ip(),
                    port=self.log_port
                    )
            except ConnectionRefusedError:
                print(f'Failed to insantiate Log Server at port {self.LOG_PORT}')
                raise
        self.log_server.start()

    def initialize_gui(self):
        """ Initializes basic GUI display """

        ip_str, ip_str_2, log_str = '', '', ''
        if self.master:
            self.main_window.setWindowTitle('Launch Control (Master)')
        if self.proxy:
            if self.staticproxy:
                self.main_window.setWindowTitle('Launch Control (Staticproxy)')
            else:
                self.main_window.setWindowTitle('Launch Control (Proxy)')
            ip_str = 'Master (Local) '
            ip_str_2 = f' ({get_ip()})'
            log_str = 'Master'
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
        self._configure_client_search()
        self._configure_debug()
        self._configure_debug_combo_select()
        self._configure_logfile()
        self._configure_logging()
        self._configure_autoscroll_off()

        self.main_window.force_update()

    def update_proxy(self, new_msg):
        """ Updates the proxy with new content using the buffer terminal continuously"""

        self.main_window.terminal.append(re.sub(r'!~\d+~!', '', new_msg))
        if not self.autoscroll_off:
            try:
                self.main_window.terminal.moveCursor(QtGui.QTextCursor.End)
            except TypeError:
                pass
        self.update_index = int(re.findall(r'\d+', re.findall(r'!~\d+~!', new_msg)[-1])[0])

    def kill_servers(self):
        """ Kills all servers connected to the logger, including the Log GUI and Log Server"""

        client_data = copy.deepcopy(self.client_data)
        del client_data['logger_GUI']

        for server_data in client_data.values():
            if 'port' in server_data:
                stop_client = ClientBase(host=server_data['ip'], port=server_data['port'])
                stop_client.close_server()
        self.gui_server.stop()
        self.log_server.stop()

    def update(self, text):
        """ Runs an update when new text comes through """

        self.main_window.configure_widgets()
        self.main_window.update_widgets()

        #Check for disconnection events
        self.check_disconnection(text)

        # Handle new connections
        self.update_connection()

        # Update terminal
        self.update_terminal(text)

        # Chop log file if date has changed
        self.chop_log_file()

        if self.disconnection:
            self.disconnect()

    def chop_log_file(self):
        """ Checks if date has changed, and chops logfile accordingly"""

        if self.date_str is not None:
            # if date has changed, move to new log file with new date
            if self.date_str != datetime.now().strftime("%Y_%m_%d"):
                self.start_stop_logging(master_log=True)

            # TEST TEST TEST
            # --------------------------------------------------------------------------------------------------------------------------------------------------------------------
            if self.minute_str != datetime.now().strftime("%M"):
                self.start_stop_logging()
            # --------------------------------------------------------------------------------------------------------------------------------------------------------------------


    def _configure_client_search(self):
        self.main_window.client_search.textChanged.connect(self._search_clients)

    def _configure_clicks(self):
        """ Configures what to do upon clicks """

        self.main_window.close_server.pressed.connect(self._stop_server)

    def _search_clients(self):

        search_str = self.main_window.client_search.text()

        clients = self.gui_client.get_container_info('clients')

        self.main_window.client_list.clear()
        self.client_list.clear()

        if search_str is not "":
            for client, info in clients.items():
                self.client_list[client] = QtWidgets.QListWidgetItem(client)
                # look for clients that have name or ip address containing search string
                if search_str in client or search_str in self.client_data[client]['ip']:
                    self.main_window.client_list.addItem(self.client_list[client])
                self.client_list[client].setToolTip(info)
        else:
            for client, info in clients.items():
                self.client_list[client] = QtWidgets.QListWidgetItem(client)
                self.main_window.client_list.addItem(self.client_list[client])
                self.client_list[client].setToolTip(info)

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
                self.gui_logger.info('Attempting to remove from LogClients manually')
                self._close_dangling(client_to_stop)
        else:
            self._close_dangling(client_to_stop)

    def _close_dangling(self, client_to_stop):

        # Cannot connect to the server and close, must remove.
        # WARNING: might result in dangling threads

        try:
            client_port_to_stop = self.port_list[client_to_stop]
            port_found = True
        except KeyError:
            port_found = False

        if port_found and client_port_to_stop in self.log_server._server.clients:
            c = self.port_list[client_to_stop]
            c.close()
            closing(c)
            self.log_server._server.clients.discard(c)
            self.main_window.client_list.takeItem(self.main_window.client_list.row(self.client_list[client_to_stop]))
            del self.port_list[client_to_stop]
            del self.client_list[client_to_stop]
            del self.log_service.client_data[client_to_stop]
            del self.client_data[client_to_stop]
            self.gui_logger.info(f'Client disconnected: {client_to_stop}')

        # If we can't find the client connected to the server, just remove it
        else:
            self.gui_logger.warn(f'No matching client connected to LogServer: {client_to_stop}')
            try:

                # The following two member variables don't exist for a proxy.
                if not self.proxy:
                    self.main_window.client_list.takeItem(self.main_window.client_list.row(self.client_list[client_to_stop]))
                    del self.port_list[client_to_stop]
                    del self.log_service.client_data[client_to_stop]
                    del self.client_list[client_to_stop]
                    del self.client_data[client_to_stop]
                else:
                    self.gui_client.remove_client_list_entry(client_to_stop)
                self.gui_logger.info(f'Hard kill of {client_to_stop} successfull.')

            except:
                pass

    def _device_clicked(self, index):
        """ Configures behavior for device double click

        :param index: (QModelIndex) index of file clicked on
        """

        # clear the client search bar and display all clients
        self.main_window.client_search.setText("")
        #self._search_clients()

        filepath = self.main_window.devices.model().filePath(index)

        # Check if it is an actual config file
        if not os.path.isdir(filepath):

            # Find the name of the server and device config file
            device_server = os.path.basename(os.path.dirname(filepath))
            device_config = os.path.basename(filepath)[:-5]

            self.gui_logger.info(f'Launching device {device_server} '
                                         f'with configuration {device_config}')

            # Initial configurations: All flags down.
            server_debug_flag = '0'

            # Raise flags if selected in combobox
            if self.debug and self.debug_level == "pylabnet_server":
                server_debug_flag = '1'

            server_port = np.random.randint(1024, 49151)
            launch_device_server(
                server=device_server,
                dev_config=device_config,
                log_ip=self.host,
                log_port=self.log_port,
                server_port=server_port,
                debug=server_debug_flag
            )

    def _script_clicked(self, index):
        """ Configures behavior for script double click

        :param index: (QModelIndex) index of file clicked on
        """

        # clear the client search bar and display all clients
        self.main_window.client_search.setText("")
        #self._search_clients()

        filepath = self.main_window.scripts.model().filePath(index)

        # Check if it is an actual config file
        if not os.path.isdir(filepath):

            # Find the name of the config file
            script_name = os.path.basename(os.path.dirname(filepath))
            script_config = os.path.basename(filepath)[:-5]

            self.gui_logger.info(f'Launching device {script_name} '
                                         f'with configuration {script_config}')

            # Initial configurations: All flags down.
            debug_flag, server_debug_flag = '0', '0'

            # Raise flags if selected in combobox
            if self.debug:
                if self.debug_level == "launcher":
                    debug_flag = '1'
                elif self.debug_level == "pylabnet_server":
                    server_debug_flag = '1'

            # Build client list cmdline arg
            client_index = 1
            bash_cmd = ''
            for client in self.client_list:
                bash_cmd += ' --client{} {} --ip{} {}'.format(
                    client_index, remove_spaces(client), client_index, self.client_data[client]['ip']
                )

                # Add device ID of client's corresponding hardware, if applicable
                if 'device_id' in self.client_data[client]:
                    bash_cmd += ' --device_id{} {}'.format(client_index, self.client_data[client]['device_id'])

                # Add port of client's server, if applicable
                if 'port' in self.client_data[client]:
                    bash_cmd += ' --port{} {}'.format(client_index, self.client_data[client]['port'])

                # If this client has relevant .ui file, pass this info
                if 'ui' in self.client_data[client]:
                    bash_cmd += ' --ui{} {}'.format(client_index, self.client_data[client]['ui'])

                client_index += 1

            launch_script(
                script=script_name,
                config=script_config,
                log_ip=self.host,
                log_port=self.log_port,
                debug_flag=debug_flag,
                server_debug_flag=server_debug_flag,
                num_clients=len(self.client_list),
                client_cmd=bash_cmd
            )

    def _load_scripts(self):
        """ Loads all relevant scripts/devices from filesystem"""

        # Load scripts with configuraitons
        script_dir = os.path.join(get_config_directory(), 'scripts')
        if os.path.isdir(script_dir):
            model = QtWidgets.QFileSystemModel()
            model.setRootPath(script_dir)
            self.main_window.scripts.setModel(model)
            self.main_window.scripts.setRootIndex(model.index(script_dir))
            self.main_window.scripts.hideColumn(1)
            self.main_window.scripts.hideColumn(2)
            self.main_window.scripts.hideColumn(3)
        self.main_window.scripts.doubleClicked.connect(self._script_clicked)

        # Load device config files
        device_dir = os.path.join(get_config_directory(), 'devices')
        if os.path.isdir(device_dir):
            model = QtWidgets.QFileSystemModel()
            model.setRootPath(device_dir)
            self.main_window.devices.setModel(model)
            self.main_window.devices.setRootIndex(model.index(device_dir))
            self.main_window.devices.hideColumn(1)
            self.main_window.devices.hideColumn(2)
            self.main_window.devices.hideColumn(3)
        self.main_window.devices.doubleClicked.connect(self._device_clicked)

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
            if 'device_id: ' in info:
                self.client_data[client]['device_id'] = info.split('device_id: ')[1].split('\n')[0]

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
            if 'device_id: ' in clients[client]:
                self.client_data[client]['device_id'] = clients[client].split('device_id: ')[1].split('\n')[0]



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
                if 'device_id: ' in clients[client]:
                    self.client_data[client]['device_id'] = clients[client].split('device_id: ')[1].split('\n')[0]

    def _configure_autoscroll_off(self):
        self.main_window.autoscroll_off_check.toggled.connect(self._update_autoscroll_setting)

    # Defines what to do if debug radio button is clicked.
    def _configure_debug(self):
        self.main_window.debug_radio_button.toggled.connect(self._update_debug_settings)

    def _configure_logging(self):
        """ Defines what to do if the Start/Stop Logging button is clicked """
        self.main_window.logfile_status_button.toggled.connect(lambda: self.start_stop_logging(master_log=False))

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

    def _update_autoscroll_setting(self):
        if self.main_window.autoscroll_off_check.isChecked():
            self.autoscroll_off = True
        else:
            self.autoscroll_off = False

    def _kill(self):
        """ Kills launch control and all child servers if master """

        if not self.proxy:
            self.kill_servers()

        self.main_window.close()

    def start_stop_logging(self, master_log=False):
        """ Starts or stops logging to file depending on situation

        :master_log: (bool) If True, this function is called as initial setup function of
            filesaving for the master launch control. In this case a log path as specified
            in the config file is chosen.
        """

        if self.main_window.logfile_status_button.isChecked() or master_log:

            date_str = datetime.now().strftime("%Y_%m_%d")
            time_str = datetime.now().strftime("%H_%M_%S")

            # TEST TEST TEST
            # --------------------------------------------------------------------------------------------------------------------------------------------------------------
            self.minute_str = datetime.now().strftime("%M")
            # --------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Actually start logging
            filename = f'logfile_{date_str}_{time_str}'

            # Get logging file from json.
            filepath = None
            if master_log:
                try:
                    config_dict = load_config('static_proxy')
                    filepath = config_dict['logger_path']
                except:
                    self.main_window.terminal.setText('Critical error: '
                                                      'no logger_path found in static_proxy.json')
                    self.main_window.force_update()
                    time.sleep(10)
                    raise
            # Or from filepath selector.
            else:
                filepath = self.main_window.file_viewer.model().filePath(
                    self.main_window.file_viewer.selectionModel().currentIndex()
                )

            try:
                self.log_service.add_logfile(
                    name=filename,
                    dir_path=filepath
                )
            except Exception as error_msg:
                print(f'Failed to start logging to file {os.path.join(filepath, filename)}.\n{error_msg}')

            self.log_service.gui_logger.info(f'Started logging to file {os.path.join(filepath, filename)}.')

            # Change button color and text
            self.main_window.logfile_status_button.setStyleSheet("background-color: red")
            self.main_window.logfile_status_button.setText('Stop logging to file')
            self.main_window.logfile_status_indicator.setChecked(True)

            # Add previous text to logfile
            if self.main_window.log_previous.isChecked():
                self.log_service.gui_logger.info(
                    f'Previous log terminal content: \n{self.main_window.terminal.toPlainText()}'
                    f'\n---------------------------'
                )

            # Pass current date of logfile for day-chopping purposes
            self.date_str = date_str

        else:

            # Change button color and text
            self.main_window.logfile_status_button.setStyleSheet("background-color: green")
            self.main_window.logfile_status_button.setText('Start logging to file')
            self.main_window.logfile_status_indicator.setChecked(False)

            # Actually stop logging
            self.log_service.stop_latest_logfile()

            # Set date string to None so that logfile does not get updated anymore
            self.date_str = None


class WriteStream:
    """ Wrapper for sys.stdout to pipe to gui """

    def __init__(self,queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)


class UpdateReceiver(QtCore.QObject):
    """ Process to run in separate thread to monitor for logger updates"""

    update_signal = QtCore.pyqtSignal(str)

    def __init__(self, queue, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.queue = queue

    @QtCore.pyqtSlot()
    def run(self):
        while True:
            text = self.queue.get()
            self.update_signal.emit(text)


class ProxyUpdater(QtCore.QObject):
    """ Process to run in separate thread to synchronize proxy GUI """

    update_signal = QtCore.pyqtSignal(str)

    def __init__(self, controller, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.controller = controller

    @QtCore.pyqtSlot()
    def run(self):
        while True:
            time.sleep(0.1)
            # Check clients and update
            self.controller._pull_connections()

            # Get buffer terminal
            buffer_terminal = self.controller.gui_client.get_text('buffer')

            # Parse buffer terminal to get part of the message that is new
            new_msg = buffer_terminal[buffer_terminal.rfind(f'!~{self.controller.update_index+1}~!'):-1]

            # Check if this failed
            if new_msg == '':

                # Check if the buffer is ahead of our last update
                up_str = re.findall(r'!~\d+~!', new_msg)
                if len(up_str) > 0:
                    up_in = int(re.findall(r'\d+', up_str[0]))
                    if up_in > self.controller.update_index:
                        new_msg = buffer_terminal

            # If we have a new message to add, add it
            if new_msg != '':
                self.update_signal.emit(new_msg)

            # Chop log file if date has changed (and if logging to file)
            self.controller.chop_log_file()



def main():
    """ Runs the launch controller """

    hide_console()
    log_controller = Controller()
    run(log_controller)

def main_proxy():
    """ Runs the launch controller overriding commandline arguments in proxy mode """

    log_controller = Controller(proxy=True)
    run(log_controller)

def main_master():
    """ Runs the launch controller overriding commandline arguments in master mode """

    log_controller = Controller(master=True)
    run(log_controller)

def main_staticproxy():
    """ Runs the launch controller overriding commandline arguments in staticproxy mode """

    log_controller = Controller(staticproxy=True)
    run(log_controller)

def run(log_controller):
    """ Runs the launch controller once a Controller is instantiated"""

    # Refresh thread
    update_thread = QtCore.QThread()

    if log_controller.proxy:

        # Set up GUI
        log_controller.initialize_gui()
        log_controller.start_gui_server()

        # Set up update thread
        updater = ProxyUpdater(log_controller)
        updater.update_signal.connect(log_controller.update_proxy)

    else:
        # Redirect sys.stdout to queue
        queue = Queue()
        sys.stdout = WriteStream(queue)

        # Instantiate GUI
        log_controller.start_logger()
        log_controller.initialize_gui()
        log_controller.start_gui_server()

        # Start logging os in master mode
        if log_controller.master:
            log_controller.start_stop_logging(master_log=True)

        # Start thread to listen for updates
        updater = UpdateReceiver(queue)
        updater.update_signal.connect(log_controller.update)

    updater.moveToThread(update_thread)
    update_thread.started.connect(updater.run)
    update_thread.start()
    log_controller.app.exec_()


if __name__ == '__main__':
    main_staticproxy()
