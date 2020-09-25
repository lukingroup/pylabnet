
import pylabnet.utils.pulseblock.pulse as po
from pylabnet.utils.helper_methods import load_config
import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule
from pylabnet.hardware.staticline import staticline
from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import DIOPulseBlockHandler


""" Generic script for monitoring counts from a counter """

import numpy as np
import time
import socket
import pyqtgraph as pg
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogClient
from pylabnet.scripts.pause_script import PauseService
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server import si_tt
from pylabnet.utils.helper_methods import unpack_launcher, load_config, get_gui_widgets, get_legend_from_graphics_view

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout, QTableWidgetItem







class PulseMaster:

    # Generate all widget instances for the .ui to use
    # _plot_widgets, _legend_widgets, _number_widgets = generate_widgets()

    def __init__(self, hd, config, ui='pulsemaster', logger_client=None, server_port=None):
        """ TODO
        """

        self.hd = hd
        self.log = logger_client

        # Load config dict.
        self.config_dict = load_config(
            config_filename=config,
            logger=self.log
        )

         # Load DIO assignment.
        self.DIO_assignment_dict = load_config(
                config_filename=self.config_dict['DIO_dict'],
                logger=self.log
        )

        # Instantiate GUI window
        self.gui = Window(
            gui_template=ui,
            host=socket.gethostbyname(socket.gethostname()),
            port=server_port
        )

        # Get Widgets
        self.widgets = get_gui_widgets(self.gui, DIO_table=1)

        # Populate DIO table
        self.populate_dio_table()

    def populate_dio_table(self):
        '''Populate DIO assignment table from DIO assignment dict.
        '''
        dio_table = self.widgets['DIO_table']

        # Define table size
        dio_table.setRowCount(len(self.DIO_assignment_dict.keys()))
        dio_table.setColumnCount(2)

        for i, (dio_name, dio_bit) in enumerate(self.DIO_assignment_dict.items()):
            #Populate it
            dio_table.setItem(i , 0, QTableWidgetItem(str(dio_name)))
            dio_table.setItem(i , 1, QTableWidgetItem(str(dio_bit)))

            self.log.info('DIO settings successfully loaded.')

    def run(self):
        """ Runs an iteration of checks for updates and implements
        """

        time.sleep(1)
        self.gui.force_update()


def launch(**kwargs):
    """ Launches the pulsemaster script """

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    # Instantiate Pulsemaster
    try:
        pulsemaster = PulseMaster(
            hd=clients['zi_hdawg'], logger_client=logger, server_port=kwargs['server_port'], config=kwargs['config']
        )
    except KeyError:
        logger.error('Please make sure the module names for required servers and GUIS are correct.')
        time.sleep(15)
        raise

    # try:
    #     config = load_config('counters')
    #     ch_list = list(config['channels'])
    #     plot_1 = list(config['plot_1'])
    #     plot_2 = list(config['plot_2'])
    #     plot_list = [plot_1, plot_2]
    # except:
    #     config = None
    #     ch_list = [7, 8]
    #     plot_list = [[7], [8]]


    # # Set parameters
    # if params is None:
    #     params = dict(bin_width=2e10, n_bins=1e3, ch_list=ch_list, plot_list=plot_list)
    # monitor.set_params(**params)

    # Run

    while True:
        pulsemaster.run()
