import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.helper_methods import generate_widgets


class Monitor:
    CALIBRATION = [1e-4]

    def __init__(self, pm_clients, gui_client, logger=None):
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_clients: (client, list of clients) clients of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)
        if isinstance(pm_clients, list):
            self.pm = pm_clients
        else:
            self.pm = [pm_clients]

        self.running = False
        self._initialize_gui()

    def run(self):

        self.running = True
        while self.running:

            for channel, pm in enumerate(self.pm):
            
                # Get all current values
                p_in = pm.get_power(0)
                p_ref = pm.get_power(1)
                efficiency = np.sqrt(p_ref/(p_in*self.CALIBRATION[channel]))
                values = [p_in, p_ref, efficiency]

                plot_label_list = [
                    f'input_graph_{channel}',
                    f'reflection_graph_{channel}',
                    f'coupling_graph_{channel}'
                ]
                number_label_list = [
                    f'input_power_{channel}',
                    f'reflection_power_{channel}',
                    f'coupling_{channel}'
                ]

                # Update GUI
                for plot_no, plot in enumerate(plot_label_list):
                    self.gui.set_scalar(values[plot_no], number_label_list[plot_no])
                    self.plots[plot_no] = np.append(self.plots[plot_no][:-1], values[plot_no])
                    self.gui.set_curve_data(
                        data=self.plots[plot_no],
                        plot_label=plot,
                        curve_label=plot,
                    )


    def _initialize_gui(self):
        """ Instantiates GUI by assigning widgets """

        self.graphs, self.legends, self.numbers = generate_widgets(
            dict(graph_widget=3, legend_widget=3, number_widget=3)
        )
        self.plots = []

        for channel in range(len(self.pm)):

            # Graphs
            plot_label_list = [
                f'input_graph_{channel}',
                f'reflection_graph_{channel}',
                f'coupling_graph_{channel}'
            ]
            for index, label in enumerate(plot_label_list):
                self.gui.assign_plot(
                    plot_widget=self.graphs[index],
                    plot_label=label,
                    legend_widget=self.legends[index]
                )
                self.gui.assign_curve(
                    plot_label=label,
                    curve_label=label
                )
            self.plots.append(np.zeros(1000))

            # Numbers
            number_label_list = [
                f'input_power_{channel}',
                f'reflection_power_{channel}',
                f'coupling_{channel}'
            ]
            for index, label in enumerate(number_label_list):
                self.gui.assign_scalar(
                    scalar_widget=self.numbers[index],
                    scalar_label=label
                )
