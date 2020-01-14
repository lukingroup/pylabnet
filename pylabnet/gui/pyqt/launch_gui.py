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
    main_window = Window(app, gui_template='wavemetermonitor_4ch')

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

    # plot_1 = 'Channel 1 Monitor'
    # curve_1 = 'Curve 1'
    # plot_2 = 'Channel 2 Monitor'
    # curve_2 = 'Curve 2'
    #
    # main_window.assign_plot(
    #     plot_widget='graph_widget_1',
    #     plot_label=plot_1,
    #     legend_widget='legend_widget_1'
    # )
    # main_window.assign_curve(
    #     plot_label=plot_1,
    #     curve_label=curve_1
    # )
    # main_window.assign_curve(
    #     plot_label=plot_1,
    #     curve_label=curve_2
    # )
    #
    # main_window.assign_plot(
    #     plot_widget='graph_widget_2',
    #     plot_label=plot_2,
    #     legend_widget='legend_widget_2'
    # )
    # main_window.assign_curve(
    #     plot_label=plot_2,
    #     curve_label=curve_1
    # )
    # main_window.assign_curve(
    #     plot_label=plot_2,
    #     curve_label=curve_2
    # )
    #
    # num_1 = 'Number 1'
    # main_window.assign_scalar(
    #     scalar_widget='number_widget_1',
    #     scalar_label=num_1
    # )
    #
    # bool_1 = 'Boolean 1'
    # main_window.assign_scalar(
    #     scalar_widget='boolean_widget_1',
    #     scalar_label=bool_1
    # )

    # Build list of widgets internal to .gui (script specific)
    graph_widgets = []
    legend_widgets = []
    number_widgets = []
    bool_widgets = []
    for i in range(4):
        graph_widgets.append('graph_widget_'+str(i+1))
        legend_widgets.append('legend_widget_'+str(i+1))
        bool_widgets.append('boolean_widget_'+str(i+1))
        number_widgets.append('number_widget_'+str(i+1))
    for i in range(4, 8):
        number_widgets.append('number_widget_'+str(i+1))

    # Define our plot, curve, and scalar names
    plot_1 = 'Velocity monitor'
    p1_curve_1 = 'Velocity frequency'
    p1_curve_2 = 'Velocity setpoint'
    plot_2 = 'TiSa monitor'
    p2_curve_1 = 'TiSa frequency'
    freq_1 = 'Velocity frequency'
    sp_1 = 'Velocity setpoint'
    freq_2 = 'TiSa frequency'
    lock_1 = 'Velocity lock'

    # Define mapping between key names and widget names
    plots = {
        plot_1: {
            'curves': [p1_curve_1, p1_curve_2],
            'widget': graph_widgets[0],
            'legend': legend_widgets[0]
        },
        plot_2: {
            'curves': [p2_curve_1],
            'widget': graph_widgets[1],
            'legend': legend_widgets[1]
        }
    }
    scalars = {
        freq_1: number_widgets[0],
        sp_1: number_widgets[1],
        lock_1: bool_widgets[0],
        freq_2: number_widgets[2]
    }

    main_window.assign_widgets(plots=plots, scalars=scalars)
    main_window.configure_widgets()
    main_window.set_scalar(
        value=np.random.random_sample(),
        scalar_label=sp_1
    )

    # Run the GUI until the stop button is clicked
    while not main_window.stop_button.isChecked():
        main_window.set_curve_data(
            np.random.random(1000),
            plot_label=plot_1,
            curve_label=p1_curve_1
        )
        main_window.set_curve_data(
            1 + np.random.random(1000),
            plot_label=plot_1,
            curve_label=p1_curve_2
        )
        main_window.set_curve_data(
            np.random.random(1000),
            plot_label=plot_2,
            curve_label=p2_curve_1
        )
        # main_window.set_curve_data(
        #     1 + np.random.random(1000),
        #     plot_label=plot_2,
        #     curve_label=curve_2
        # )
        main_window.set_scalar(
            value=np.random.random_sample(),
            scalar_label=freq_1
        )
        main_window.set_scalar(
            value=np.random.random_sample(),
            scalar_label=freq_2
        )
        if np.random.random_sample() > 0.5:
            main_window.set_scalar(
                value=True,
                scalar_label=lock_1
            )
        else:
            main_window.set_scalar(
                value=False,
                scalar_label=lock_1
            )

        main_window.update_widgets()
        app.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
