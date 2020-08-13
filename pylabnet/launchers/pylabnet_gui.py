""" Script that launches and continuously runs a GUI window

Normally, this is meant to be invoked from within a Launcher object (see launcher.py).
However, you can also call this directly, with command-line arguments:
:arg --logport: port number of log server
:arg --guiport: (optional) port number to use for GUI server. Notes:
    (1) if not provided, the user will be prompted to enter a port number in the commandline
    (2) will raise a ConnectionRefusedError if port fails
:arg --ui: (optional) the name of the server module. Notes:
    (1) should be a valid .ui file (with .ui extension removed) within pylabnet/gui/pyqt/templates,
        otherwise, FileNotFound error will be raised
    (2) if not provided, _default_template will be used
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import socket
import ctypes
import numpy as np
import os

from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.network.client_server.external_gui import Service
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient
from pylabnet.utils.helper_methods import parse_args, show_console, hide_console, create_server, load_config

import sys
import socket

# Should help with scaling issues on monitors of differing resolution
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


def main():

    # parse command line arguments
    args = parse_args()
    try:
        log_port = int(args['logport'])
    except IndexError:
        raise IndexError('logport not provided. Please provide command line arguments in the form\n"'
                         'python launch_gui.py --logip 000.000.000.000 --logport 1234 --guiport 5678 --ui uifilename')
    if 'logip' in args:
        log_ip = args['logip']
    else:
        log_ip = 'localhost'
    if 'ui' in args:
        gui_template = args['ui']
    else:
        # Get all relevant files
        ui_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'gui', 'pyqt', 'gui_templates'
        )
        files = [file for file in os.listdir(ui_directory) if (
            os.path.isfile(os.path.join(
                ui_directory, file
            )) and '.ui' in file
        )]
        show_console()
        print('Available UIs to launch:\n')
        for file in files:
            print(file[:-3])
        gui_template = input('\nPlease enter a UI name: ')
        hide_console()
    if 'guiport' in args:
        gui_port = int(args['guiport'])
    else:
        gui_port = None

    # Instantiate logger
    gui_logger = LogClient(
        host=log_ip,
        port=log_port,
        module_tag=gui_template+'_GUI',
        ui=gui_template,
        server_port=gui_port
    )

    # Loading config file
    settings = {}
    if 'config' in args:
        if args['config'] != 'None':
            settings = load_config(
                args['config'],
                logger=gui_logger
            )

    # Retrieve debug flag.
    debug = int(args['debug'])

    # Halt execution and wait for debugger connection if debug flag is up.
    if debug:
        import ptvsd
        # 5678 is the default attach port in the VS Code debug configurations
        gui_logger.info(f"Waiting for debugger to attach to PID {os.getpid()} (pylabnet_gui)")
        ptvsd.enable_attach(address=('localhost', 5678))
        ptvsd.wait_for_attach()
        breakpoint()

    gui_logger.info('Logging for gui template: {}'.format(gui_template))

    # # Create app and instantiate main window
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(
        QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
    )
    try:
        main_window = Window(app, gui_template=gui_template)
    except FileNotFoundError:
        gui_logger.warn('Could not find .ui file, '
                        'please check that it is in the pylabnet/gui/pyqt/gui_templates directory')
        raise

    # Implement config related updates
    if 'window_title' in settings:
        main_window.setWindowTitle(settings['window_title'])
        gui_logger.info(f'Set window title to {settings["window_title"]}')

    # Instantiate GUI server
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=gui_logger)

    # Make connection
    try:
        if gui_port is None:
            gui_server, gui_port = create_server(
                service=gui_service,
                logger=gui_logger,
                host=socket.gethostbyname(socket.gethostname())
            )
            gui_logger.update_data(data=dict(port=gui_port))
        else:
            gui_server = GenericServer(
                service=gui_service,
                host=socket.gethostbyname(socket.gethostname()),
                port=gui_port
            )
    except ConnectionRefusedError:
        gui_logger.warn('Tried and failed to create GUI server with \nIP:{}\nPort:{}'.format(
            socket.gethostbyname(socket.gethostname()),
            gui_port
        ))
        raise
    gui_server.start()

    # Update GUI with server-specific details
    try:
        main_window.ip_label.setText('IP Address: {}'.format(
            socket.gethostbyname(socket.gethostname())
        ))
        main_window.port_label.setText('Port: {}'.format(gui_port))
    except AttributeError:
        gui_logger.warn(f'Could not set IP Address and port labels on {gui_template}')

    # Run the GUI until the stop button is clicked
    hide_console()
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        main_window.force_update()

    gui_server.stop()


if __name__ == '__main__':
    main()
