from PyQt5 import QtWidgets

from pylabnet.gui.pyqt.external_gui import Window, Service
from pylabnet.core.generic_server import GenericServer
from pylabnet.utils.logging.logger import LogClient

import sys
import numpy as np


def main():

    # Instantiate logger
    gui_logger = LogClient(
        host='localhost',
        port=1234,
        module_tag='GUI module'
    )

    # Create app and instantiate main window
    app = QtWidgets.QApplication(sys.argv)
    main_window = Window(app)

    # Instantiate GUI server
    gui_service = Service()
    gui_service.assign_module(module=main_window)
    gui_service.assign_logger(logger=gui_logger)
    gui_server = GenericServer(
        service=gui_service,
        host='localhost',
        port=9
    )
    gui_server.start()

    # Test code
    main_window.assign_plot(
        plot_widget="graph_widget_1",
        legend_widget="legend_widget_1",
        plot_label="Channel 1 Monitor",
        curve_label="Curve 1",
        error_bars=True
    )
    # main_window.assign_plot(plot_label="Channel 1 Monitor", curve_label="Curve 2")

    main_window.assign_plot(
        plot_widget="graph_widget_2",
        legend_widget="legend_widget_2",
        plot_label="Channel 2 Monitor",
        curve_label="Curve 1"
    )
    main_window.assign_plot(plot_label="Channel 2 Monitor", curve_label="Curve 2")

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.set_data(
            np.random.random(1000),
            error=np.random.random(1000)*0.2,
            plot_label="Channel 1 Monitor",
            curve_label="Curve 1"
        )
        # main_window.set_data(
        #     1 + np.random.random(1000),
        #     plot_label="Channel 1 Monitor",
        #     curve_label="Curve 2"
        # )
        main_window.set_data(
            np.random.random(1000),
            plot_label="Channel 2 Monitor",
            curve_label="Curve 1"
        )
        main_window.set_data(
            1 + np.random.random(1000),
            plot_label="Channel 2 Monitor",
            curve_label="Curve 2"
        )
        app.processEvents()
    main_window.close_gui()


if __name__ == '__main__':
    main()
