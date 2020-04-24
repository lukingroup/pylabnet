import time
import subprocess
import numpy as np
import sys
import os
import socket
from pylabnet.utils.logging import logger
from pylabnet.utils.helper_methods import parse_args
from pylabnet.gui.pyqt import external_gui

# # For debugging
# time.sleep(15)

# For operation of main
from pylabnet.hardware.counter.swabian_instruments import cnt_monitor
from pylabnet.scripts.counter import monitor_counts


class Launcher:

    _GUI_LAUNCH_SCRIPT = 'launch_gui.py'
    _SERVER_LAUNCH_SCRIPT = 'launch_server.py'

    def __init__(self, script=None, server_req=None, gui_req=None, auto_connect=True, name=None, params=None):
        """ Instantiates Launcher object

        :param script: script module to launch. The module needs:
            launch() method
        :param server_req: list of modules containing necessary servers. The module needs:
            (1) main() method to instantiate Service and run the server
            (1) Client() class, so that we can instantiate a client from this thread and pass it to the script
        :param gui_req: list of gui names to instantiate (names of .ui files, excluding .ui extension)
        :param auto_connect: (bool) whether or not to automatically connect if there is a single instance of the
            required server already running
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
            self.log_port = int(self.args['logport'])
            self.num_clients = int(self.args['numclients'])
        except IndexError:
            raise

        # Connect to logger
        self.logger = self._connect_to_logger()

        # Find all servers with port numbers and store them as a dictionary
        self.connectors = {}
        self._scan_servers()

        # Containers for clients
        self.gui_clients = {}
        self.clients = {}

    def launch(self):
        try:
            self._launch_guis()
            self._launch_servers()
            self._launch_scripts()
        except Exception as e:
            print(e)
            time.sleep(20)
            raise

    def _connect_to_logger(self):
        log_client = logger.LogClient(host='localhost', port=self.log_port, module_tag=self.name)
        return logger.LogHandler(logger=log_client)

    def _scan_servers(self):

        for client_index in range(self.num_clients):

            # Check if there is a port for this client, instantiate connector if so
            port_name = 'port{}'.format(client_index + 1)
            client_name = self.args['client{}'.format(client_index+1)]
            if port_name in self.args:
                self.connectors[client_name] = Connector(
                    name=client_name,
                    ip=self.args['ip{}'.format(client_index+1)],
                    port=self.args[port_name]
                )

            # Check for a ui file as well, if it is a GUI
            ui_name = 'ui{}'.format(client_index + 1)
            if ui_name in self.args:
                self.connectors[client_name].set_ui(self.args[ui_name])

    def _launch_new_gui(self, gui):
        """ Launches a new GUI and connects to it """

        connected = False
        timeout = 0
        while not connected and timeout < 1000:
            try:
                gui_port = np.random.randint(1, 9999)
                subprocess.Popen('start /min "{}, {}" /wait {} {} --logport {} --guiport {} --ui {}'.format(
                    gui,
                    time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime()),
                    sys.executable,
                    os.path.join(os.path.dirname(os.path.realpath(__file__)),self._GUI_LAUNCH_SCRIPT),
                    self.log_port,
                    gui_port,
                    gui
                ), shell=True)
                connected = True
            except ConnectionRefusedError:
                self.logger.warn(f'Failed to start {gui} GUI server on localhost with port {gui_port}')
                timeout += 1
                time.sleep(0.01)
        if timeout == 1000:
            self.logger.error(f'Failed to start {gui} GUI server on localhost')
            raise ConnectionRefusedError()

        # Connect to GUI, store client. Try several times, since it may take some time to actually launch the server
        connected = False
        timeout = 0
        while not connected and timeout < 1000:
            try:
                self.gui_clients[gui] = external_gui.Client(host='localhost', port=gui_port)
                connected = True
            except ConnectionRefusedError:
                timeout += 1
                time.sleep(0.01)

        # If we could connect after roughly 10 seconds, something is wrong and we should raise an error
        if timeout == 1000:
            self.logger.error('Failed to connect client to newly instantiated {} server at \nIP: localhost'
                              '\nPort: {}'.format(gui, gui_port))
            raise ConnectionRefusedError()

    def _connect_to_gui(self, gui, host, port):
        """ Connects to a GUI server with host and port details

        :param gui: (str) name of .ui file to use
        :param host: (str) IP address of server to connect to
        :param port: (int) port number of server to connect to
        """
        if host == socket.gethostbyname(socket.gethostname()):
            host = 'localhost'
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
                    if gui+'_GUI' == connector.ui:
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

    def _launch_new_server(self, module):
        """ Launches a new server

        :param module: (obj) reference to the service object which can be launched via module.Service()
        """

        connected = False
        timeout = 0
        while not connected and timeout < 1000:
            try:
                server_port = np.random.randint(1, 9999)
                server = module.__name__.split('.')[-1]
                subprocess.Popen(f'start /min "{server}, {time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())}"'
                                 f'/wait {sys.executable} '
                                 f'{os.path.join(os.path.dirname(os.path.realpath(__file__)),self._SERVER_LAUNCH_SCRIPT)} '
                                 f'--logport {self.log_port} --serverport {server_port} --server {server}', shell=True)
                connected = True
            except ConnectionRefusedError:
                self.logger.warn(f'Failed to start {server} server on localhost with port {server_port}')
                timeout += 1
                time.sleep(0.01)
            if timeout == 1000:
                self.logger.error(f'Failed to start {server} server on localhost')
                raise ConnectionRefusedError()

        # Connect to server, store client. Try several times, since it may take some time to actually launch the server
        connected = False
        timeout = 0
        while not connected and timeout < 1000:
            try:
                self.clients[server] = module.Client(host='localhost', port=server_port)
                connected = True
            except ConnectionRefusedError:
                timeout += 1
                time.sleep(0.01)

        # If we could connect after roughly 10 seconds, something is wrong and we should raise an error
        if timeout == 1000:
            self.logger.error('Failed to connect client to newly instantiated {} server at \nIP: localhost'
                              '\nPort: {}'.format(server, server_port))
            raise ConnectionRefusedError()

    def _connect_to_server(self, module, host, port):
        """ Connects to a new server 

        :param module: (object) module from which client can be instantiated using module.Client()
        :param host: (str) IP address of host
        :param port: (int) port number of host
        """

        server = module.__name__
        if host == socket.gethostbyname(socket.gethostname()):
            host = 'localhost'
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
                if module.__name__+'_server' == connector.name:
                    matches.append(connector)
            num_matches = len(matches)

            # If there are no matches, launch and connect to the server manually
            if num_matches == 0:
                self._launch_new_server(module)

            # If there is exactly 1 match, try to connect automatically
            elif num_matches == 1 and self.auto_connect:
                self._connect_to_server(module, host=matches[0].ip, port=matches[0].port)

            # If there are multiple matches, force the user to choose in the launched console
            else:
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

    def _launch_scripts(self):
        """ Launch the scripts to be run sequentially in this thread """

        for script in self.script:

            script.launch(
                logger=self.logger,
                clients=self.clients,
                guis=self.gui_clients,
                logport=self.log_port,
                params=self.params
            )


class Connector:

    def __init__(self, name=None, ip=None, port=None):
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
        """ Summarizes connector properties

        :return: (str) summary of all properties
        """
        return 'Name: {}\nIP: {}\nPort: {}\nUI: {}'.format(self.name, self.ip, self.port, self.ui)


# Example implementation: launches full count monitor application
def main():

    launcher = Launcher(
        script=[monitor_counts],
        server_req=[cnt_monitor],
        gui_req=['count_monitor'],
        params=None
    )
    launcher.launch()


if __name__ == '__main__':
    main()
