""" Script that launches a server.

NOTE: MAKE SURE THAT THE SERVER MODULE IS IMPORTED IN THIS SCRIPT

Normally, this is meant to be invoked from within a Launcher object (see launcher.py).
However, you can also call this directly, with command-line arguments:
:arg --logport: port number of log server
:arg --serverport: (optional) port number to use for server. Notes:
    (1) if not provided, the user will be prompted to enter a port number in the commandline
    (2) this script does not explicitly provide ConnectionRefusedError handling. Two (non-exclusive) options:
        (i) Implement in server.launch() method
        (ii) Implement in launcher.py module (DONE)
:arg --server: (optional) the name of the server module. Notes:
    (1) should be the name of the module from which the desired server can be instantiated
    (2) module must explicitly be imported in this script
            (we could consider adding auto-import functionality for selected/all modules at a later time)
    (3) module must have a launch(**kwargs) method for instantiating server (and prerequisites) with parameters
        :param logger: instance of LogClient class to use for logging
        :param port: (int) port number
        :param name: (str) name to use as the server's module tag.
            Recommended to use the module name itself (server.__name__)
"""

import sys
import time

from pylabnet.utils.helper_methods import parse_args
from pylabnet.utils.logging.logger import LogClient

# # For debugging
# print('Waiting for debugger to connect')
# time.sleep(30)

# IMPORTANT: make sure all relevant modules are imported, otherwise you will not be able to use them via this launcher!
try:
    from pylabnet.gui.pyqt import external_gui
    from pylabnet.hardware.counter.swabian_instruments import cnt_monitor
except Exception as e:
    print('Please make sure all necessary imports are possible')
    time.sleep(20)
    raise

DEFAULT_SERVER = 'external_gui'


def main():

    # parse command line arguments
    args = parse_args()
    try:
        log_port = int(args['logport'])
    except IndexError:
        raise IndexError('Please provide command line arguments in the form\n"'
                         'python launch_gui.py --logport 1234 --serverport 5678 --server servername')
    if 'serverport' in args:
        server_port = int(args['serverport'])
    else:
        server_port = int(input('Please enter a server port value: '))
    if 'server' in args:
        server = args['server']
    else:
        server = input('Please enter a server module name: ')

    # Instantiate logger
    server_logger = LogClient(
        host='localhost',
        port=log_port,
        module_tag=server+'_server',
        server_port=server_port
    )

    # Instantiate module
    mod_inst = getattr(sys.modules[__name__], server)
    mod_inst.launch(logger=server_logger, port=server_port, name=server)


if __name__ == '__main__':
    main()
