""" Launches the logger + graphical display """

import sys
import socket
import os
import time
from io import StringIO
from pylabnet.utils.logging.logger import LogService
from pylabnet.core.generic_server import GenericServer
from PyQt5 import QtWidgets, QtGui
from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient

def main():

    # Hardwire log and GUI server ports
    LOG_PORT = 1234
    GUI_PORT = 5678
    LG = 'Logger GUI'
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

    # Add script launching tree
    file_model = QtWidgets.QFileSystemModel()
    file_model.setRootPath(os.path.dirname(os.getcwd()))
    main_window.file_tree.setModel(file_model)

    # Instantiate GUI server so it can be connected to externally
    gui_logger = LogClient(
        host='localhost',
        port=log_port,
        module_tag=LG
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

    # Add GUI server to list of connected clients
    client_list = {LG: QtWidgets.QListWidgetItem(LG)}
    port_list = {LG: [port for port in log_server._server.clients][0]}
    main_window.client_list.addItem(client_list[LG])
    client_list[LG].setToolTip(log_service.client_data[LG])

    # Display terminal text and clear
    main_window.terminal.append(sys.stdout.getvalue())
    sys.stdout.truncate(0)
    sys.stdout.seek(0)

    disconnection_flag = False
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.update_widgets()

        # Check stdout and update
        current_output = sys.stdout.getvalue()
        if current_output is not '':

            # Update output
            main_window.terminal.append(current_output)
            main_window.terminal.moveCursor(QtGui.QTextCursor.End)

            # Clear stdout
            sys.stdout.truncate(0)
            sys.stdout.seek(0)

            # check for deletion
            if 'Client disconnected' in current_output or disconnection_flag:
                disconnection_flag = True

            # Check for any additions from/to client list
            # PUT INSIDE TRY
            port_to_add = [port for port in log_server._server.clients if port not in port_list.values()]
            client_to_add = [client for client in log_service.client_data if client not in client_list]

            if len(client_to_add) > 0:
                client = client_to_add[0]
                client_list[client] = QtWidgets.QListWidgetItem(client)
                main_window.client_list.addItem(client_list[client])
                client_list[client].setToolTip(log_service.client_data[client])
                if len(port_to_add) > 0:
                    port_list[client] = port_to_add[0]

        if disconnection_flag:
            to_del = [client for (client, port) in port_list.items() if port not in log_server._server.clients]
            for client in to_del:
                main_window.client_list.takeItem(main_window.client_list.row(client_list[client]))
                del client_list[client]
                del port_list[client]
                del log_service.client_data[client]
                disconnection_flag = False


        main_window.force_update()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
