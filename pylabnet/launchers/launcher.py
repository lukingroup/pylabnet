""" Generic module for launching pylabnet scripts

This script should be invoked from the command line with
relevant commandline arguments. For example,

    'start "dummy_testing_server, 2020-12-21, 02:54:27"
    "C:\\Users\\mbhas\\pylabnet\\venv\\pylabnet-test\\Scripts\\python.exe"
    "C:\\Users\\mbhas\\pylabnet\\pylabnet\\launchers\\launcher.py"
    --logip 192.168.0.106 --logport 21189 --script dummy_testing
    --num_clients 1 --config three_fake_devices --debug 0 --server_debug 0
    --client1 logger_GUI --ip1 192.168.0.106 --port1 44847 --ui1 logger_remote'

This command is usually constructed automatically via the Launch Control
(see pylabnet.launchers.launch_control for details).

The script must have a config dictionary in pylabnet/configs/scripts/my_script.
This dict must contain the required device servers and the path to the script,
which is a python file that has a launch(**kwargs) method that launches the script.
Example config dict:

    {
    "servers" : [
        {
            "type" : "dummy",
            "config" : "mihir_computer",
            "auto_connect" : "False"
        },
        {
            "type" : "dummy",
            "config" : "other_device"
        },
        {
            "type" : "dummy",
            "config" : "science_tool"
        }
    ],
    "script" : "C:\\Users\\mbhas\\pylabnet\\pylabnet\\scripts\\deviceless_test.py"
}

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
from pylabnet.utils.helper_methods import get_ip, parse_args, hide_console, create_server, load_config, load_script_config, load_device_config, launch_device_server
from pylabnet.network.client_server import external_gui
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.gui.pyqt.external_gui import ParameterPopup, fresh_popup, warning_popup


class Launcher:

    def __init__(self):
        """ Instantiates Launcher object

        Parses commandline arguments, connects to logger, loads script
        config dictionary, scans available servers
        """

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
        self.service = None

    def launch(self):
        """ Launches/connects to required servers and runs the script """

        if "servers" in self.config_dict:
            self._launch_servers()
        if not ('script_server' in self.config_dict and self.config_dict['script_server'] == 'False'):
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
                self.logger.warn(f'No device_id on client {client_name}, None assigned as default')
                device_id = None
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
        :param device_id: (str) device_id of server
        """

        server = module

        self.logger.info('Trying to connect to active {} server\nHost: {}\nPort: {}'.format(server, host, port))
        self._add_to_clients(module, device_id, host, port)

    def _add_to_clients(self, module, device_id, host, port):
        """Adds the associated client at host and port to the internal client dictionary that will be passed
        onto the launched script.
        Dictionary is formatted as a two layer dictionary, where first layer is indexed by the module name,
        and second is indexed by the device_id. This enables an easy lookup

        :param module: (str) name of the hardware/server module (e.g. nidaqmx)
        :param device_id: (str) device id
        :param host: (str) host of server
        :param port: (int) port number of server
        """
        server = module

        spec = importlib.util.spec_from_file_location(
            module,
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'servers',
                module+'.py'
            )
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.clients[(server, device_id)] = mod.Client(host=host, port=port)

    def _launch_servers(self):
        """ Searches through active servers and connects/launches them """

        for server in self.config_dict['servers']:
            module_name = server['type']
            if "script" in server and server["script"] == "True":
                server_config = load_script_config(
                    module_name,
                    server['config'],
                    self.logger
                )
            else:
                server_config = load_device_config(
                    module_name,
                    server['config'],
                    self.logger
                )

            matches = []
            for connector in self.connectors.values():
                # Add servers that have the correct name and ID
                if (connector.name.startswith(module_name)) and (server_config['device_id'] == connector.device_id):
                    matches.append(connector)

            if 'auto_connect' in server and server['auto_connect'] == 'False':
                auto_connect = False
            else:
                auto_connect = True

            self._connect_matched_servers(matches, module_name, server['config'], server_config, auto_connect)

    def _connect_matched_servers(self, matches, module, config_name, config, auto_connect):
        """ Connects to a list of servers that have been matched to a given device
        module.

        :param matches: (list) list of matching server modules
        :param module: (str) name of module to launch (e.g. nidaqmx)
        :param config_name: (str) name of the config file for the device server
        :param config: (dict) actual config dict for the server
        :param auto_connect: (bool) whether or not to automatically connect to the device/server
        """

        device_id = config['device_id']

        num_matches = len(matches)
        module_name = module

        if 'auto_launch' in config and config['auto_launch'] == 'False':
            launch_stop = True
        else:
            launch_stop = False

        # If there are no matches, launch and connect to the server manually
        if num_matches == 0:
            if launch_stop:
                self.logger.info(f'No No active servers matching module {module_name}'
                                 'were found. Please instantiate manually.')
                raise Exception('Server must be launched manually prior to script')
            else:
                self.logger.info(f'No active servers matching module {module_name}'
                                ' were found. Instantiating a new server.')
                host, port = launch_device_server(
                    server=module,
                    dev_config=config_name,
                    log_ip=self.log_ip,
                    log_port=self.log_port,
                    server_port=np.random.randint(1024, 49151),
                    debug=self.server_debug,
                    logger=self.logger
                )

                tries=0
                while tries<10:
                    try:
                        self._connect_to_server(module, host, port, device_id)
                        tries = 11
                    except ConnectionRefusedError:
                        time.sleep(0.1)
                        tries += 1
                if tries == 10:
                    self.logger.error(f'Failed to connect to {module}')

        # If there is exactly 1 match, try to connect automatically
        elif num_matches == 1 and auto_connect:
            self.logger.info(f'Found exactly 1 match for {module_name}.')
            self._connect_to_server(module, matches[0].ip, matches[0].port, device_id)

        # If there are multiple matches, force the user to choose in the launched console
        else:
            msg_str = 'Found relevant server(s) already running.\n'
            self.logger.info(msg_str)
            for index, match in enumerate(matches):
                msg_str = ('------------------------------------------\n'
                        + '                    ({})                   \n'.format(index + 1)
                        + match.summarize())
                self.logger.info(msg_str)
            self.logger.info('------------------------------------------\n\n'
                             'Which server would you like to connect to?\n'
                             'Please enter a choice from {} to {}.'.format(1, len(matches)))
            app, popup = fresh_popup(index=int)
            self.waiting_flag = True
            popup.parameters.connect(self.find_index)
            while self.waiting_flag:
                app.processEvents()
            self.logger.info(f'User chose ({self.use_index})')

            # If the user's choice falls within a relevant GUI, attempt to connect.
            try:
                if self.use_index - 1 < 0:
                    raise IndexError
                host, port = matches[self.use_index - 1].ip, matches[self.use_index - 1].port
                self._connect_to_server(module, host, port, device_id)

            # If the user's choice did not exist, just launch a new GUI
            except IndexError:
                self.logger.info('Launching new server')
                host, port = launch_device_server(
                    server=module,
                    dev_config=config_name,
                    log_ip=self.log_ip,
                    log_port=self.log_port,
                    server_port=np.random.randint(1024, 49151),
                    debug=self.server_debug,
                    logger=self.logger
                )

                tries=0
                while tries<10:
                    try:
                        self._connect_to_server(module, host, port, device_id)
                        tries = 11
                    except ConnectionRefusedError:
                        time.sleep(0.1)
                        tries += 1
                if tries == 10:
                    self.logger.error(f'Failed to connect to {module}')
            hide_console()

    def find_index(self, params):
        """ Loads the index of device to use """

        self.use_index = params['index']
        self.waiting_flag = False


    def _launch_scripts(self):
        """ Launch the scripts to be run sequentially in this thread """

        spec = importlib.util.spec_from_file_location(
            self.name,
            self.config_dict['script']
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.logger.info(f'Launching script {self.name}')

        mod.launch(
            logger=self.logger,
            loghost=self.log_ip,
            clients=self.clients,
            logport=self.log_port,
            config=self.config,
            server_port=self.script_server_port,
            service=self.service
        )

    def _launch_script_server(self):
        """ Launches a GenericServer attached to this script to enable closing
        """

        if 'script_service' in self.config_dict and self.config_dict['script_service'] == 'True':
            spec = importlib.util.spec_from_file_location(
                self.name,
                self.config_dict['script']
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.service = mod.Service()
        else:
            self.service = ServiceBase()
        self.service.assign_logger(logger=self.logger)

        self.script_server, self.script_server_port = create_server(
            service=self.service,
            logger=self.logger,
            host=get_ip()
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

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        warning_popup(traceback.format_exc())

