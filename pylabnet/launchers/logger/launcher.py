import time
from pylabnet.utils.helper_methods import parse_args


class Launcher:

    def __init__(self, script=None, server_req=None, gui_req=None):
        """ Instantiates Launcher object

        :param script: script to launch
        :param server_req: list of server module names to instantiate
        :param gui_req: list of gui names to instantiate
        """

        self.script = script
        self.server_req = server_req
        self.gui_req = gui_req

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
    launcher = Launcher()
    for connector in launcher.connectors.values():
        print(connector.summarize())
    time.sleep(10)


if __name__ == '__main__':
    main()
