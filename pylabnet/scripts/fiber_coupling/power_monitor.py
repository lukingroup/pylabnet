from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.pyqt.gui_handler import GUIHandler


class Monitor:

    def __init__(self, pm_client, gui_client, logger=None):
        """ Instantiates a monitor for 2-ch power meter with GUI

        :param pm_client: client of power meter
        :param gui_client: client of monitor GUI
        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)
        self.pm = pm_client

    def run(self):

        pass