""" Runs a GUI window

Instantiates client to connect to Logger. Runs a Window server
Continuously updates GUI configuration and output. Can press the stop button + close the window to deactivate the GUI
Can connect to the GUI and update data by creating a GUI client.

Must tie the GUI to a .ui file that can be created in QtDesigner
"""

from PyQt5 import QtWidgets, QtCore

from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient
from pylabnet.utils.helper_methods import parse_args

import sys
import socket
import numpy as np

# Should help with scaling issues on monitors of differing resolution
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

_default_template = "count_monitor"


def main():

    # parse command line arguments
    args = parse_args()
    try:
        log_port = args['logport']
    except IndexError:
        raise IndexError('Please provide command line arguments in the form\n"'
                         'python launch_gui.py --logport 1234 --ui uifilename')
    if 'ui' in args:
        gui_template = args['ui']
    else:
        gui_template = None
        ui_file = _default_template

    # Instantiate logger
    gui_logger = LogClient(
        host='localhost',
        port=log_port,
        module_tag='Counter GUI Server',
        ui=ui_file
    )

    gui_logger.info('Logging for gui template: {}'.format(gui_template))

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    try:
        main_window = Window(app, gui_template=gui_template)
    except FileNotFoundError:
        gui_logger.warn('Could not find .ui file, '
                        'please check that it is in the pylabnet/gui/pyqt/gui_templates directory')
        raise

    # Instantiate GUI server
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=gui_logger)

    # Connect trying different port numbers if failed
    connected = False
    while not connected:
        port_num = np.random.randint(1, 9999)
        try:
            gui_server = GenericServer(
                service=gui_service,
                host='localhost',
                port=port_num
            )
            connected = True
        except ConnectionRefusedError:
            gui_logger.warn('Tried and failed to create server with \nIP:{}\nPort:{}'.format(
                socket.gethostbyname(socket.gethostname()),
                port_num
            ))
    gui_logger.update_data(data=dict(port=port_num))
    gui_server.start()

    # Update GUI with server-specific details
    main_window.ip_label.setText('IP Address: {}'.format(
        socket.gethostbyname(socket.gethostname())
    ))
    main_window.port_label.setText('Port: {}'.format(port_num))

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        main_window.force_update()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
