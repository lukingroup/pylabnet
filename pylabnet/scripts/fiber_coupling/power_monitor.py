from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.helper_methods import generate_widgets


class Monitor:

    def __init__(self, pm_client, gui_client, logger=None, channels=1):
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_client: client of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        :param channels: (int) number of channels
        """

        self.log = LogHandler(logger)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)
        self.pm = pm_client
        self.channels = channels

        self.running = False
        self._initialize_gui()

    def run(self):

        self.running = True
        while self.running:
            pass

    def _initialize_gui(self):
        """ Instantiates GUI by assigning widgets """

        self.graphs, self.legends, self.numbers = generate_widgets(
            dict(graph_widget=3, legend_widget=3, number_widget=3)
        )

        for channel in range(self.channels):

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
