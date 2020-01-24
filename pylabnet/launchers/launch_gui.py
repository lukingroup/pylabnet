""" Runs a GUI window

Instantiates client to connect to Logger. Runs a Window server
Continuously updates GUI configuration and output. Can press the stop button + close the window to deactivate the GUI
Can connect to the GUI and update data by creating a GUI client.

Must tie the GUI to a .ui file that can be created in QtDesigner
"""

from PyQt5 import QtWidgets

from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient

import sys
import socket


def main():

    # Instantiate logger
    gui_logger = LogClient(
        host='localhost',
        port=1234,
        module_tag='GUI module'
    )

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)

    if len(sys.argv) > 1:
        gui_template = sys.argv[1]
    else:
        gui_template = None
    main_window = Window(app, gui_template=gui_template)

    # Instantiate GUI server
    port_num = 9
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
    try:
        main_window.ip_label.setText('IP Address: {}'.format(
            socket.gethostbyname(socket.gethostname())
        ))
        main_window.port_label.setText('Port: {}'.format(port_num))
    except AttributeError:
        pass

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        main_window.force_update()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
