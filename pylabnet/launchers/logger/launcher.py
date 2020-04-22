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
        self.servers = self._scan_servers()

    def _scan_servers(self):

        servers = {}
        for client_index in range(self.num_clients):

            # Check if there is a port for this client
            port_name = 'port{}'.format(client_index + 1)
            if port_name in self.args:
                servers[self.args['client{}'.format(client_index+1)]] = int(self.args[port_name])

        return servers


def main():
    launcher = Launcher()
    print(launcher.servers)
    time.sleep(10)


if __name__ == '__main__':
    main()
