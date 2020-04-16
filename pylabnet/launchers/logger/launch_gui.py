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

import sys
import socket
import numpy as np


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


def main():

    # Retrieve GUI template from command line argument
    gui_template = 'count_monitor'

    # Instantiate logger
    gui_logger = LogClient(
        host='localhost',
        port=1234,
        module_tag='Counter GUI Server'
    )

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    main_window = Window(app, gui_template=gui_template)

    # Instantiate GUI server
    port_num = np.random.randint(0, 9999)
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=gui_logger)
    gui_server = GenericServer(
        service=gui_service,
        host='localhost',
        port=port_num
    )
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
