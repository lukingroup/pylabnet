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
    main_window = Window(app, gui_template='wavemetermonitor')

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

    plot_1 = 'Channel 1 Monitor'
    curve_1 = 'Curve 1'
    plot_2 = 'Channel 2 Monitor'
    curve_2 = 'Curve 2'

    main_window.assign_plot(
        plot_widget='graph_widget_1',
        plot_label=plot_1,
        legend_widget='legend_widget_1'
    )
    main_window.assign_curve(
        plot_label=plot_1,
        curve_label=curve_1
    )
    main_window.assign_curve(
        plot_label=plot_1,
        curve_label=curve_2
    )

    main_window.assign_plot(
        plot_widget='graph_widget_2',
        plot_label=plot_2,
        legend_widget='legend_widget_2'
    )
    main_window.assign_curve(
        plot_label=plot_2,
        curve_label=curve_1
    )
    main_window.assign_curve(
        plot_label=plot_2,
        curve_label=curve_2
    )

    num_1 = 'Number 1'
    main_window.assign_scalar(
        scalar_widget='number_widget_1',
        scalar_label=num_1
    )

    bool_1 = 'Boolean 1'
    main_window.assign_scalar(
        scalar_widget='boolean_widget_1',
        scalar_label=bool_1
    )

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.configure_widgets()
        main_window.set_curve_data(
            np.random.random(1000),
            plot_label=plot_1,
            curve_label=curve_1
        )
        main_window.set_curve_data(
            1 + np.random.random(1000),
            plot_label=plot_1,
            curve_label=curve_2
        )
        main_window.set_curve_data(
            np.random.random(1000),
            plot_label=plot_2,
            curve_label=curve_1
        )
        main_window.set_curve_data(
            1 + np.random.random(1000),
            plot_label=plot_2,
            curve_label=curve_2
        )
        main_window.set_scalar(
            value=np.random.random_sample(),
            scalar_label=num_1
        )
        if np.random.random_sample() > 0.5:
            main_window.set_scalar(
                value=True,
                scalar_label=bool_1
            )
        else:
            main_window.set_scalar(
                value=False,
                scalar_label=bool_1
            )

        main_window.update_widgets()
        app.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
