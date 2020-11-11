
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, get_gui_widgets
from pylabnet.gui.pyqt.external_gui import Window

import socket
import time
import numpy as np


class TopticaFilterWheelController:
    """ Class for controlling Toptica scan and laser properties """

    def __init__(self, filterwheel1, filterwheel2, gui='toptica_filterwheels', logger=None, port=None):


        self.log = LogHandler(logger)

        # Setup GUI
        self.gui = Window(
            gui_template=gui,
            host=socket.gethostbyname(socket.gethostname()),
            port=port
        )

        # Get Widgets
        self.widgets = get_gui_widgets(
            self.gui,
            comboBox_filter1=1,
            comboBox_filter2=1,
            nd_label=1
        )

        # Fill comboboxes
        for filterlabel1, filterlabel2 in zip(filterwheel1.filters.values(), filterwheel2.filters.values()):
            self.widgets['comboBox_filter1'].addItems(filterlabel1)
            self.widgets['comboBox_filter2'].addItems(filterlabel2)

        # Setup stylesheet.
        self.gui.apply_stylesheet()

    def run(self, check_vals=False):
        """ Runs an iteration of checks for updates and implements

        :param check_vals: (bool) whether or not to check the values of current and temp
        """
        pass

def launch(**kwargs):

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    filterwheel1 = clients['toptica_filterwheel1']
    filterwheel2 = clients['toptica_filterwheel2']

    # Instantiate Monitor script
    toptica_controller = TopticaFilterWheelController(
        filterwheel1=filterwheel1,
        filterwheel2=filterwheel2,
        logger=logger,
        port=kwargs['server_port']
    )

    toptica_controller.gui.app.exec_()


