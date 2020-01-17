from PyQt5 import QtWidgets

from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient

import sys
import socket

# TODO: Set gui template as command-line argument


def main():

    # Instantiate logger
    gui_logger = LogClient(
        host='localhost',
        port=1234,
        module_tag='GUI module'
    )

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    main_window = Window(app, gui_template='wavemetermonitor_4ch')

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
    main_window.ip_label.setText('IP Address: {}'.format(
        socket.gethostbyname(socket.gethostname())
    ))
    main_window.port_label.setText('Port: {}'.format(port_num))

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        app.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
