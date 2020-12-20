""" Generic module for launching pylabnet scripts

NOTE: Requires windows (TODO: make OS agnostic)
"""

import time
import subprocess
import numpy as np
import sys
import traceback
import os
import socket
import importlib.util
from pylabnet.utils.logging import logger
from pylabnet.utils.helper_methods import parse_args, show_console, hide_console, create_server, load_config, load_script_config, load_device_config, launch_device_server
from pylabnet.network.client_server import external_gui
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.generic_server import GenericServer


class Launcher:

    def __init__(self):
        """ Instantiates Launcher object

        :param name: (str) name of script to launch (directory within configs/scripts)
        :param config: (str) name of config file (specific .json file within configs/scripts/name)
        """
        # self.script = script
        # self.server_req = server_req
        # self.gui_req = gui_req
        # self.auto_connect = auto_connect
        # self.config = config
        # self.params = params
        # self.use_script_server = script_server

        # Get command line arguments as a dict
        self.args = parse_args()
        self.name = self.args['script']
        self.config = self.args['config']
        self.log_ip = self.args['logip']
        self.log_port = int(self.args['logport'])
        self.debug = int(self.args['debug'])
        self.server_debug = int(self.args['server_debug'])
        self.num_clients = int(self.args['num_clients'])

        # Connect to logger
        self.logger = self._connect_to_logger()

        # Load config
        self.config_dict = load_script_config(
            script=self.name,
            config=self.config, 
            logger=self.logger
        )

        # Halt execution and wait for debugger connection if debug flag is up.
        if self.debug == 1:
            import ptvsd
            import os
            # 5678 is the default attach port in the VS Code debug configurations
            self.logger.info(f"Waiting for debugger to attach to PID {os.getpid()} (launcher)")
            ptvsd.enable_attach(address=('localhost', 5678))
            ptvsd.wait_for_attach()
            breakpoint()

        # Register new exception hook.
        def log_exceptions(exc_type, exc_value, exc_traceback):
            """Handler for unhandled exceptions that will write to the logs"""
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.logger.error(f"Uncaught exception: {error_msg}")

        sys.excepthook = log_exceptions

        # Connectors are LogClients connected to the current LogServer
        # Find all servers with port numbers and store them as a dictionary
        self.connectors = {}
        self._scan_servers()

        # Containers for clients that servers that this launcher creates / connects to
        self.clients = {}

        # Script server
        self.script_server_port = None
        self.script_server = None

    def launch(self):
        """ Checks for GUIS/servers, instantiates required, and launches script(s)"""

        if "servers" in self.config_dict:
            self._launch_servers()
        if not ('script_server' in self.config_dict and bool(self.config_dict['script_server'])):
            self._launch_script_server()
        hide_console()
        self._launch_scripts()

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


            #First see if there is a device id
            try:
                device_id = self.args['device_id{}'.format(client_index+1)]
            except KeyError:
                self.logger.error(f'No device_id on client {client_name}, None assigned as default')
            try:
                self.connectors[client_name] = Connector(
                            name=client_name,
                            ip=self.args['ip{}'.format(client_index+1)],
                            port=self.args[port_name],
                            device_id=device_id
                        )
            except KeyError:
                pass

            # Check for a ui file as well, if it is a GUI
            ui_name = 'ui{}'.format(client_index + 1)
            try:
                self.connectors[client_name].set_ui(self.args[ui_name])
            except KeyError:
                pass

    def _connect_to_server(self, module, host, port, device_id=None):
        """ Connects to a server and stores the client as an attribute, to be used in the main script(s)

        :param module: (object) module from which client can be instantiated using module.Client()
        :param host: (str) IP address of host
        :param port: (int) port number of host
        """

        server = module

        self.logger.info('Trying to connect to active {} server\nHost: {}\nPort: {}'.format(server, host, port))
        self._add_to_clients(module, device_id, host, port)

    def _add_to_clients(self, module, device_id, host, port):
        """Adds the associated client at host and port to the internal client dictionary that will be passed
        onto the launched script.
        Dictionary is formatted as a two layer dictionary, where first layer is indexed by the module name,
        and second is indexed by the device_id. This enables an easy lookup"""
        server = module.__name__.split('.')[-1]

        if server not in self.clients:
            self.clients[server] = {} #Instantiate a blank dictionary corresponding to the server module
        
        spec = importlib.util.spec_from_file_location(
            module,
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'servers'
            )
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader_exec_module(mod)
        self.clients[server][device_id] = mod.Client(host=host, port=port)

    def _launch_servers(self):
        """ Searches through active servers and connects/launches them """

        for server in self.config_dict['servers']:
            module_name = server['type']
            server_config = load_device_config(
                module_name,
                server['config'],
                self.logger
            )

            matches = []
            for connector in self.connectors.values():
                # Add servers that have the correct name and ID
                if (connector.name.startswith(module_name+'_server_')) and (server_config['device_id'] == connector.device_id):
                    matches.append(connector)

            if 'auto_connect' in server and not bool(server['auto_connect']):
                auto_connect = False
            else:
                auto_connect = True

            self._connect_matched_servers(matches, module_name, server['config'], server_config, auto_connect)

    def _connect_matched_servers(self, matches, module, config_name, config, auto_connect):
        """ Connects to a list of servers that have been matched to a given device
        module. """

        device_id = config['device_id']

        num_matches = len(matches)
        module_name = module

        # If there are no matches, launch and connect to the server manually
        if num_matches == 0:
            self.logger.info(f'No active servers matching module {module_name}'
                            ' were found. Instantiating a new server.')
            launch_device_server(
                server=module,
                config=config_name,
                log_ip=self.log_ip,
                log_port=self.log_port,
                server_port=np.random.randint(1024, 49151),
                debug=self.server_debug
            )

        # If there is exactly 1 match, try to connect automatically
        elif num_matches == 1 and auto_connect:
            self.logger.info(f'Found exactly 1 match for {module_name}.')
            self._connect_to_server(module, matches[0].ip, matches[0].port, device_id)

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
                self._connect_to_server(module, host, port, device_id)

            # If the user's choice did not exist, just launch a new GUI
            except IndexError:
                self.logger.info('Launching new server')
                launch_device_server(
                    server=module,
                    config=config_name,
                    log_ip=self.log_ip,
                    log_port=self.log_port,
                    server_port=np.random.randint(1024, 49151),
                    debug=self.server_debug
                )
            hide_console()

    def _launch_scripts(self):
        """ Launch the scripts to be run sequentially in this thread """

        spec = importlib.util.spec_from_file_location(
            self.name,
            self.config_dict['script']
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader_exec_module(mod)
        
        mod.launch(
            logger=self.logger,
            loghost=self.log_ip,
            clients=self.clients,
            logport=self.log_port,
            config=self.config,
            server_port=self.script_server_port
        )

    def _launch_script_server(self, service=None):
        """ Launches a GenericServer attached to this script to enable closing

        :param service: (optional), child of ServiceBase to enable server functionality
            NOTE: not yet implemented, can be used in future e.g. for pause server
        """

        if service is None:
            service = ServiceBase()

        self.script_server, self.script_server_port = create_server(
            service=service,
            logger=self.logger,
            host=socket.gethostbyname_ex(socket.gethostname())[2][0]
        )
        self.script_server.start()

        self.logger.update_data(data=dict(
            port=self.script_server_port
        ))


class Connector:
    """ Generic container for information about current clients to the LogServer"""

    def __init__(self, name=None, ip=None, port=None, device_id=None):
        """ Instantiates connector

        :param name: (str, optional) name of the client
        :param ip: (str, optional) IP address of the client
        :param port: (str, optional) port number of the client
        :param device_id: (str, optional) device ID the client's associated device
        """

        self.name = name
        self.ip = ip
        self.port = port
        self.ui = None
        self.device_id = device_id

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

    def set_id(self, device_id):
        """ Sets the device ID

        :param device_id: (str) device ID
        """
        self.device_id = device_id

    def summarize(self):
        """ Summarizes connector properties. Useful for debugging/logging purposes

        :return: (str) summary of all properties
        """
        return 'Name: {}\nIP: {}\nPort: {}\nUI: {}\nDevice ID: {}'.format(self.name, self.ip, self.port, self.ui, self.device_id)


def main():
    """ Launches a script """

    script = Launcher()
    script.launch()
