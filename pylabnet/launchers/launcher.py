""" Generic module for launching pylabnet scripts

NOTE: Requires windows (TODO: make OS agnostic)
NOTE: Only operational on a single machine (TODO: make network compatible)
NOTE: the script module(s) must have a launch() method that can handle kwargs
        :param logger: instance of the LogClient object for logging
        :param logport: (int) port of the log server
        :param clients: dictionary containing all relevant clients in the form e.g.
            {client_1_module.__name__: client_1_instance,
            client_2_module.__name__: client_2_instance, ...}
        :param guis: dictionary containing all relevant GUI clients in the form:
            {ui_filename_1: ui_client_1, ui_filename_2: ui_client_2, ...}
        :param params: arbitrary object containing all script parameters
NOTE: the server module(s) must have a launch() method that can handle kwargs
        :param logger: instance of the LogClient object for loggin
        :param port: port number to use for opening a server

Implements the Launcher class which is used to launch desired pylabnet script(s).
If multiple scripts are provided, they are launched sequentially in this process.
Before launching the script(s), it will check the running GUI's and servers connected
to the main LogServer, and try to instantiate any required servers and GUIs in
separate processes using the pylabnet_gui.py and pylabnet_server.py scripts.

This is meant to be executed by "double-click" action in the log_display GUI, but
can in principle be invoked directly from the command line with appropriate
arguments containing information about the currently running LogServer and all of
its active clients. See log_display.py, Controller._clicked() method for details

Example useage of this class in order to make a script for launching an application
script "monitor_counts.py" that requires a server to be running (provided in
pylabnet.hardware.counter.swabian_instruments.cnt_monitor.py), as well as a GUI
with the template 'count_monitor.ui'. The following .py file should be placed in the
pylabnet.launchers directory

    from .launcher import Launcher
    from pylabnet.hardware.counter.swabian_instruments import cnt_monitor
    from pylabnet.scripts.counter import monitor_counts

    def main():

        launcher = Launcher(
            script=[monitor_counts],
            server_req=[cnt_monitor],
            gui_req=['count_monitor'],
            params=[None]
        )
        launcher.launch()


    if __name__ == '__main__':
        main()

"""

import time
import subprocess
import numpy as np
import sys
import os
import socket
from pylabnet.utils.logging import logger
from pylabnet.utils.helper_methods import parse_args, show_console, hide_console
from pylabnet.gui.pyqt import external_gui


class Launcher:

    _GUI_LAUNCH_SCRIPT = 'pylabnet_gui.py'
    _SERVER_LAUNCH_SCRIPT = 'pylabnet_server.py'

    def __init__(self, script=None, server_req=None, gui_req=None, auto_connect=True, name=None, params=None):
        """ Instantiates Launcher object

        :param script: script modules to launch. Each module needs to have a launch() method
        :param server_req: list of modules containing necessary servers. The module needs:
            (1) launch() method to instantiate Service and run the server (see pylabnet_server.py for details)
            (2) Client() class, so that we can instantiate a client from this thread and pass it to the script
        :param gui_req: list of gui names to instantiate (names of .ui files, excluding .ui extension)
        :param auto_connect: (bool) whether or not to automatically connect if there is a single instance of the
            required server already running
        :param name: (str) desired name that will appear as the "process" name for the script invoking the
            Launcher object. Can be left blank, and the names of the script module(s) will be used
        :param params: (list) parameters for each script to launch
        """
        self.script = script
        self.server_req = server_req
        self.gui_req = gui_req
        self.auto_connect = auto_connect
        self.params = params
        if name is None:
            if self.script is None:
                self.name = 'Generic Launcher'
            else:
                self.name = ''
                for scr in script:
                    self.name += scr.__name__.split('.')[-1]
                    self.name += '_'
                self.name += 'script'
        else:
            self.name = name

        # Get command line arguments as a dict
        self.args = parse_args()

        try:
            self.log_ip = self.args['logip']
            self.log_port = int(self.args['logport'])
            self.num_clients = int(self.args['numclients'])
            self.debug = int(self.args['debug'])
            self.server_debug = int(self.args['server_debug'])
            self.gui_debug = int(self.args['gui_debug'])
        except IndexError:
            raise

        # Connect to logger
        self.logger = self._connect_to_logger()

        # Halt execution and wait for debugger connection if debug flag is up.
        if self.debug == 1:
            import ptvsd
            import os
            # 5678 is the default attach port in the VS Code debug configurations
            self.logger.info(f"Waiting for debugger attach to PID {os.getpid()} (launcher_script)")
            ptvsd.enable_attach(address=('localhost', 5678))
            ptvsd.wait_for_attach()
            breakpoint()

        # Find all servers with port numbers and store them as a dictionary
        self.connectors = {}
        self._scan_servers()

        # Containers for clients
        self.gui_clients = {}
        self.clients = {}

    def launch(self):
        """ Checks for GUIS/servers, instantiates required, and launches script(s)"""

        try:
            self._launch_guis()
            self._launch_servers()
            self._launch_scripts()
        except Exception as e:
            self.logger.error(e)

    def _connect_to_logger(self):
        """ Connects to the LogServer"""

        log_client = logger.LogClient(host=self.log_ip, port=self.log_port, module_tag=self.name)
        return logger.LogHandler(logger=log_client)

    def _scan_servers(self):
        """ Scans all servers/GUIs connected as clients to the LogServer and adds them to internal attributes"""

        for client_index in range(self.num_clients):

            # Check if there is a port for this client, instantiate connector if so
            port_name = 'port{}'.format(client_index + 1)
            client_name = self.args['client{}'.format(client_index+1)]
            try:
                self.connectors[client_name] = Connector(
                            name=client_name,
                            ip=self.args['ip{}'.format(client_index+1)],
                            port=self.args[port_name]
                        )
            except KeyError:
                pass

            # Check for a ui file as well, if it is a GUI
            ui_name = 'ui{}'.format(client_index + 1)
            try:
                self.connectors[client_name].set_ui(self.args[ui_name])
            except KeyError:
                pass

    def _launch_new_gui(self, gui):
        """ Launches a new GUI and connects to it

        :param gui: (str) name of the .ui file to use as a template
        """

        connected = False
        timeout = 0
        host = socket.gethostbyname(socket.gethostname())
        while not connected and timeout < 1000:
            try:
                gui_port = np.random.randint(1, 9999)
                subprocess.Popen('start /min "{}, {}" /wait "{}" "{}" --logip {} --logport {} --guiport {} --ui {} --debug {}'.format(
                    gui+'_GUI',
                    time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime()),
                    sys.executable,
                    os.path.join(os.path.dirname(os.path.realpath(__file__)),self._GUI_LAUNCH_SCRIPT),
                    self.log_ip,
                    self.log_port,
                    gui_port,
                    gui,
                    self.gui_debug
                ), shell=True)
                connected = True
            except ConnectionRefusedError:
                self.logger.warn(f'Failed to start {gui} GUI server on {host} with port {gui_port}')
                timeout += 1
                time.sleep(0.01)
        if timeout == 1000:
            self.logger.error(f'Failed to start {gui} GUI server on {host}')
            raise ConnectionRefusedError()

        # Connect to GUI, store client. Try several times, since it may take some time to actually launch the server
        connected = False
        timeout = 0
        while not connected and timeout < 1000:
            try:
                self.gui_clients[gui] = external_gui.Client(host=host, port=gui_port)
                connected = True
            except ConnectionRefusedError:
                timeout += 1
                time.sleep(0.01)

        # If we could connect after roughly 10 seconds, something is wrong and we should raise an error
        if timeout == 1000:
            self.logger.error(f'Failed to connect client to newly instantiated {gui} server at \nIP: {host}'
                              f'\nPort: {gui_port}')
            raise ConnectionRefusedError()

    def _connect_to_gui(self, gui, host, port):
        """ Connects to a GUI server with host and port details

        :param gui: (str) name of .ui file to use
        :param host: (str) IP address of server to connect to
        :param port: (int) port number of server to connect to
        """

        self.logger.info('Trying to connect to active GUI Server\nHost: {}\nPort: {}'.format(host, port))
        try:
            self.gui_clients[gui] = external_gui.Client(host=host, port=port)
        except ConnectionRefusedError:
            self.logger.warn('Failed to connect. Instantiating new GUI instead')
            self._launch_new_gui(gui)

    def _launch_guis(self):
        """ Searches through active GUIs to find and connect to/launch relevant ones """

        if self.gui_req is not None:
            for gui in self.gui_req:
                matches = []
                for connector in self.connectors.values():

                    # If we have a match, add it
                    if gui == connector.ui:
                        matches.append(connector)
                num_matches = len(matches)

                # If there are no matches, launch and connect to the GUI manually
                if num_matches == 0:
                    self.logger.info('No active GUIs matching {} were found. Instantiating a new GUI'.format(gui))
                    self._launch_new_gui(gui)

                # If there's 1 match, and we can connect automatically, try that
                elif num_matches == 1 and self.auto_connect:
                    host, port = matches[0].ip, matches[0].port
                    self._connect_to_gui(gui, host, port)

                # If there are multiple matches, force the user to choose in the launched console
                else:
                    msg_str = 'Found relevant GUI(s) already running.\n'
                    self.logger.info(msg_str)
                    show_console()
                    print(msg_str)
                    for index, match in enumerate(matches):
                        msg_str = ('------------------------------------------\n'
                                   +'                    ({})                   \n'.format(index + 1)
                                   + match.summarize())
                        print(msg_str)
                        self.logger.info(msg_str)
                    print('------------------------------------------\n\n'
                          'Which GUI would you like to connect to?\n'
                          'Please enter a choice from {} to {}.'.format(1, len(matches)))
                    use_index = int(input('Entering any other value will launch a new GUI.\n\n>> '))
                    self.logger.info(f'User chose ({use_index})')

                    # If the user's choice falls within a relevant GUI, attempt to connect.
                    try:
                        host, port = matches[use_index-1].ip, matches[use_index-1].port
                        self._connect_to_gui(gui, host, port)

                    # If the user's choice did not exist, just launch a new GUI
                    except IndexError:
                        self.logger.info('Launching new GUI')
                        self._launch_new_gui(gui)
                    hide_console()

    def _launch_new_server(self, module):
        """ Launches a new server

        :param module: (obj) reference to the module which can invoke the relevant server via module.launch()
        """

        connected = False
        timeout = 0
        host = socket.gethostbyname(socket.gethostname())
        while not connected and timeout < 1000:
            try:
                server_port = np.random.randint(1, 9999)
                server = module.__name__.split('.')[-1]

                cmd = 'start /min "{}, {}" /wait "{}" "{}" --logip {} --logport {} --serverport {} --server {} --debug {}'.format(
                    server+"_server",
                    time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime()),
                    sys.executable,
                    os.path.join(os.path.dirname(os.path.realpath(__file__)),self._SERVER_LAUNCH_SCRIPT),
                    self.log_ip,
                    self.log_port,
                    server_port,
                    server,
                    self.server_debug
                )

                subprocess.Popen(cmd, shell=True)
                connected = True
            except ConnectionRefusedError:
                self.logger.warn(f'Failed to start {server} server on {host} with port {server_port}')
                timeout += 1
                time.sleep(0.01)
            if timeout == 1000:
                self.logger.error(f'Failed to start {server} server on {host}')
                raise ConnectionRefusedError()

        # Connect to server, store client. Try several times, since it may take some time to actually launch the server
        connected = False
        timeout = 0
        while not connected and timeout < 10:
            try:
                self.clients[server] = module.Client(host=host, port=server_port)
                connected = True
            except ConnectionRefusedError:
                timeout += 1

        # If we could connect after roughly 10 seconds, something is wrong and we should raise an error
        if timeout == 1000:
            self.logger.error(f'Failed to connect client to newly instantiated {server} server at \nIP: {host}'
                              f'\nPort: {server_port}')
            raise ConnectionRefusedError()

    def _connect_to_server(self, module, host, port):
        """ Connects to a server and stores the client as an attribute, to be used in the main script(s)

        :param module: (object) module from which client can be instantiated using module.Client()
        :param host: (str) IP address of host
        :param port: (int) port number of host
        """

        server = module.__name__.split('.')[-1]
        self.logger.info('Trying to connect to active {} server\nHost: {}\nPort: {}'.format(server, host, port))
        try:
            self.clients[server] = module.Client(host=host, port=port)
        except ConnectionRefusedError:
            self.logger.warn('Failed to connect. Instantiating new server instead')
            self._launch_new_server(module)

    def _launch_servers(self):
        """ Searches through active servers and connects/launches them """

        for module in self.server_req:
            matches = []
            for connector in self.connectors.values():

                # If we find a matching server, add it
                if module.__name__.split('.')[-1]+'_server' == connector.name:
                    matches.append(connector)
            num_matches = len(matches)

            # If there are no matches, launch and connect to the server manually
            if num_matches == 0:
                self.logger.info(f'No active servers matching {module.__name__.split(".")[-1]}'
                                 'were found. Instantiating a new server')
                self._launch_new_server(module)

            # If there is exactly 1 match, try to connect automatically
            elif num_matches == 1 and self.auto_connect:
                self._connect_to_server(module, host=matches[0].ip, port=matches[0].port)

            # If there are multiple matches, force the user to choose in the launched console
            else:
                show_console()
                msg_str = 'Found relevant server(s) already running.\n'
                self.logger.info(msg_str)
                print(msg_str)
                for index, match in enumerate(matches):
                    msg_str = ('------------------------------------------\n'
                               + '                    ({})                   \n'.format(index + 1)
                               + match.summarize())
                    print(msg_str)
                    self.logger.info(msg_str)
                print('------------------------------------------\n\n'
                      'Which server would you like to connect to?\n'
                      'Please enter a choice from {} to {}.'.format(1, len(matches)))
                use_index = int(input('Entering any other value will launch a new server.\n\n>> '))
                self.logger.info(f'User chose ({use_index})')

                # If the user's choice falls within a relevant GUI, attempt to connect.
                try:
                    host, port = matches[use_index - 1].ip, matches[use_index - 1].port
                    self._connect_to_server(module, host, port)

                # If the user's choice did not exist, just launch a new GUI
                except IndexError:
                    self.logger.info('Launching new server')
                    self._launch_new_server(module)
                hide_console()

    def _launch_scripts(self):
        """ Launch the scripts to be run sequentially in this thread """

        for index, script in enumerate(self.script):

            script.launch(
                logger=self.logger,
                loghost=self.log_ip,
                clients=self.clients,
                guis=self.gui_clients,
                logport=self.log_port,
                params=self.params[index]
            )


class Connector:
    """ Generic container for information about current clients to the LogServer"""

    def __init__(self, name=None, ip=None, port=None):
        """ Instantiates connector

        :param name: (str, optional) name of the client
        :param ip: (str, optional) IP address of the client
        :param port: (str, optional) port number of the client
        """

        self.name = name
        self.ip = ip
        self.port = port
        self.ui = None

    def set_name(self, name):
        """ Sets the name of the connector

        :param name: (str) name of connector
        """
        self.name = name

    def set_ip(self, ip):
        """ Sets the IP address of the connector

        :param ip: (str) IP Address of connector
        """
        self.ip = ip

    def set_port(self, port):
        """ Sets the port number

        :param port: (str) port number
        """
        self.port = int(port)

    def set_ui(self, ui):
        """ Sets the ui filename

        :param ui: (str) ui filename (.ui attachment optional)
        """
        self.ui = ui

    def summarize(self):
        """ Summarizes connector properties. Useful for debugging/logging purposes

        :return: (str) summary of all properties
        """
        return 'Name: {}\nIP: {}\nPort: {}\nUI: {}'.format(self.name, self.ip, self.port, self.ui)
