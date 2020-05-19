import numpy as np
import socket
import sys
from PyQt5 import QtWidgets, uic, QtCore

from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.external_gui import Service
from pylabnet.gui.pyqt.external_gui import Window


def launch(logger=None, port=None, name=None):
    """ Instantiates a default main window + server

    :param logger: (LogClient) instance of LogClient for logging purposes
    :param port: (int) port number for the GUI server
    :param name: (str) name of server to display
    """

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    ui = input('Please enter the .ui file to use as a template:\n>> ')
    try:
        main_window = Window(app, gui_template=ui)
    except FileNotFoundError:
        print('Could not find .ui file, '
              'please check that it is in the pylabnet/gui/pyqt/gui_templates directory')
        raise
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=logger)

    if port is None:
        port = np.random.randint(1, 9999)
    gui_server = GenericServer(
        service=gui_service,
        host='localhost',
        port=port
    )

    gui_server.start()

    # Update GUI with server-specific details
    main_window.ip_label.setText('IP Address: {}'.format(
        socket.gethostbyname(socket.gethostname())
    ))
    main_window.port_label.setText('Port: {}'.format(port))

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        main_window.force_update()
    sys.exit(app.exec_())
