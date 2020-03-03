""" Launches the logger + graphical display """

import sys
import socket
from io import StringIO
from pylabnet.utils.logging.logger import LogService
from pylabnet.core.generic_server import GenericServer
from PyQt5 import QtWidgets, QtGui
from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient

def main():

    LOG_PORT = 1234
    GUI_PORT = 5678
    log_port, gui_port = LOG_PORT, GUI_PORT

    # Use standard logger template
    gui_template = 'logger'
    
    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    main_window = Window(app, gui_template=gui_template)

    # Instantiate log server
    log_service = LogService()
    log_server = GenericServer(service=log_service, host='localhost', port=log_port)
    log_server.start()
    sys.stdout = StringIO()

    # Update GUI with log-server-specific details
    main_window.ip_label.setText('IP Address: {}'.format(
        socket.gethostbyname(socket.gethostname())
    ))
    main_window.logger_label.setText('Logger Port: {}'.format(log_port))
    main_window.terminal.setText('Log messages will be displayed below \n')
    main_window.force_update()

    # Instantiate GUI server so it can be connected to externally
    gui_logger = LogClient(
        host='localhost',
        port=log_port,
        module_tag='Logger GUI'
    )
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=gui_logger)
    gui_server = GenericServer(
        service=gui_service,
        host='localhost',
        port=gui_port
    )
    gui_server.start()
    main_window.gui_label.setText('GUI Port: {}'.format(gui_port))

    main_window.terminal.append(sys.stdout.getvalue())
    sys.stdout.truncate(0)
    sys.stdout.seek(0)

    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()
        current_output = sys.stdout.getvalue()
        if current_output is not '':
            main_window.terminal.append(sys.stdout.getvalue())
            main_window.terminal.moveCursor(QtGui.QTextCursor.End)
            sys.stdout.truncate(0)
            sys.stdout.seek(0)
        main_window.force_update()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
