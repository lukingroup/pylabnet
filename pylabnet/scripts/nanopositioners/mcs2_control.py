from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher


class Controller:
    """ A script class for controlling MCS2 positioners + interfacing with GUI"""

    def __init__(self, nanopos_client, gui_client, log_client=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui_client: (pylabnet.network.client_server.external_gui.Client)
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        """

        self.pos = nanopos_client
        self.log = LogHandler(logger=log_client)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)

    def initialize_gui(self):
        """ Initializes the GUI (assigns channels)"""

        #TODO


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    nanopos_client = clients['smaract_mcs2']
    gui_client = guis['positioner_control']

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger)

    # Initialize all GUI channels TODO
