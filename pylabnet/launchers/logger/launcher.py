import time
import subprocess
import numpy as np
from pylabnet.utils.helper_methods import parse_args
from pylabnet.gui.pyqt import external_gui


class Launcher:

    _GUI_LAUNCH_SCRIPT = 'launch_gui.py'

    def __init__(self, script=None, server_req=None, gui_req=None, auto_connect=True):
        """ Instantiates Launcher object

        :param script: script to launch
        :param server_req: list of server module names to instantiate
        :param gui_req: list of gui names to instantiate
        :param auto_connect: (bool) whether or not to automatically connect if there is a single instance of the
            required server already running
        """

        self.script = script
        self.server_req = server_req
        self.gui_req = gui_req
        self.auto_connect = auto_connect

        # Get command line arguments as a dict
        self.args = parse_args()

        try:
            self.log_port = int(self.args['logport'])
            self.num_clients = int(self.args['numclients'])
        except IndexError:
            raise

        # Find all servers with port numbers and store them as a dictionary
        self.connectors = {}
        self._scan_servers()

        # Containers for clients
        self.gui_clients = {}
        self.clients = {}

    def launch(self):
        try:
            self._launch_guis()
        except Exception as e:
            print(e)
            time.sleep(20)
            raise

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
        while not connected:
            try:
                gui_port = np.random.randint(1, 9999)
                subprocess.Popen('start "{}, {}" /wait python {} --logport {} --guiport {} --ui {}'.format(
                    gui,
                    time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime()),
                    self._GUI_LAUNCH_SCRIPT,
                    self.log_port,
                    gui_port,
                    gui
                ), shell=True)
                time.sleep(1)
                # subprocess.Popen('python launch_gui.py --logport {} --guiport {}'.format(self.log_port, gui_port), shell=True)
                connected = True
            except ConnectionRefusedError:
                pass

        # Connect to GUI, store client
        try:
            self.gui_clients[gui] = external_gui.Client(host='localhost', port=gui_port)
        except ConnectionRefusedError as e:
            print('Failed for some reason')
            print(e)
            time.sleep(10)

    def _launch_guis(self):
        """ Searches through active GUIs to find and connect to/launch relevant ones """

        for gui in self.gui_req:
            matches = []
            for connector in self.connectors.values():

                # If we have a match, add it
                if gui is connector.ui:
                    matches.append(connector)
            num_matches = len(matches)

            # If there are no matches, launch and connect to the GUI manually
            if num_matches == 0:
                self._launch_new_gui(gui)

            # If there's 1 match, and we can connect automatically, try that
            elif num_matches == 1 and self.auto_connect:
                host, port = matches[0].ip, matches[0].port
                print('Trying to connect to GUI Server\nHost: {}\nPort: {}'.format(host, port))
                try:
                    self.gui_clients[gui] = external_gui.Client(host=host, port=port)
                except ConnectionRefusedError:
                    print('Failed to connect. Instantiating new GUI instead')
                    self._launch_new_gui(gui)

            # If there are multiple matches, force the user to choose
            else:
                # TODO
                pass


# Static methods

def create_client(self, module, ip, port):
    return module.Client(host=ip, port=port)


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


def main():
    launcher = Launcher(gui_req=['count_monitor'])
    launcher.launch()
    print('Great success')
    time.sleep(10)


if __name__ == '__main__':
    main()
