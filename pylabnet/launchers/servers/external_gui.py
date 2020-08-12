import numpy as np
import socket
import sys
import ctypes
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui

from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.external_gui import Service, Client
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import show_console, hide_console, create_server

# Should help with scaling issues on monitors of differing resolution
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


def launch(logger=None, port=None, name=None):
    """ Instantiates a default main window + server

    :param logger: (LogClient) instance of LogClient for logging purposes
    :param port: (int) port number for the GUI server
    :param name: (str) name of server to display
    """

    # # Create app and instantiate main window
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(
        QtGui.QIcon(os.path.join(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)
        )), 'devices.ico'))
    )
    show_console()
    ui = input('Please enter the .ui file to use as a template:\n>> ')
    hide_console()
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
        gui_server, port = create_server(
            service=gui_service,
            logger=logger,
            host=socket.gethostbyname(socket.gethostname())
        )
    else:
        gui_server = GenericServer(
            service=gui_service,
            host=socket.gethostbyname(socket.gethostname()),
            port=port
        )
    logger.update_data(data=dict(ui=ui, port=port))

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
    gui_server.stop()
