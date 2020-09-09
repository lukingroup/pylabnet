""" Script that launches a server.

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
"""

import importlib
import numpy as np
import os
import sys
import traceback
import ptvsd
import time

from pylabnet.utils.helper_methods import parse_args, show_console, hide_console
from pylabnet.utils.logging.logger import LogClient


def main():


    # parse command line arguments
    args = parse_args()
    try:
        log_port = int(args['logport'])
    except IndexError:
        raise IndexError('Please provide command line arguments in the form\n"'
                         'python launch_gui.py --logport 1234 --serverport 5678 --server servername')
    # If pylabnet.server is launched directly, it might not use a configs flag.
    if 'config' in args:
        configs = args['config']
    else:
        configs = None
    if 'serverport' in args:
        server_port = int(args['serverport'])
    else:
        server_port = None
    if 'server' in args:
        server = args['server']
    else:
        # Get all relevant files
        server_directory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'servers'
        )
        files = [file for file in os.listdir(server_directory) if (
            os.path.isfile(os.path.join(
                server_directory, file
            )) and '.py' in file and '__init__.py' not in file
        )]
        show_console()
        print('Available servers to launch:\n')
        for index, file in enumerate(files):
            print(f'{index}: {file[:-3]}')
        server_index = int(input('\nPlease enter a server module index: '))
        server = files[server_index][:-3]
        hide_console()
    if 'logip' in args:
        host = args['logip']
    else:
        host = 'localhost'

    # Instantiate logger
    server_logger = LogClient(
        host=host,
        port=log_port,
        module_tag=server+'_server',
        server_port=server_port
    )

        # Retrieve debug flag.
    debug = int(args['debug'])

    # Halt execution and wait for debugger connection if debug flag is up.
    if debug:
        # 5678 is the default attach port in the VS Code debug configurations
        server_logger.info(f"Waiting for debugger to attach to PID {os.getpid()} (pylabnet_server)")
        ptvsd.enable_attach(address=('localhost', 5678))
        ptvsd.wait_for_attach()
        breakpoint()

    # Register new exception hook.
    def log_exceptions(exc_type, exc_value, exc_traceback):
        """Handler for unhandled exceptions that will write to the logs"""
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        server_logger.error(f"Uncaught exception: {error_msg}")

    sys.excepthook = log_exceptions

    # Instantiate module
    try:
        mod_inst = importlib.import_module(f'servers.{server}')
    except ModuleNotFoundError:
        server_logger.error(f'No module found in pylabnet.launchers.servers named {server}.py')
        raise

    tries = 0
    update_flag = False
    while tries < 10:
        if server_port is None:
            server_port = np.random.randint(1024, 49151)
            update_flag = True
        try:
            mod_inst.launch(logger=server_logger, port=server_port, config=configs)
            if update_flag:
                server_logger.update_data(data=dict(port=server_port))
            tries = 10
        except OSError:
            server_logger.warn(f'Failed to launch server at port: {server_port}')
            tries += 1
            if tries == 10:
                raise
            

    hide_console()


if __name__ == '__main__':
    main()
