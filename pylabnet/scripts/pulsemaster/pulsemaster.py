
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

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout, QTableWidgetItem, QCompleter, QHBoxLayout, QLabel, QLineEdit


from PyQt5.QtGui import QBrush, QColor


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

        # Load dio configs.
        self.load_dio_assignment_from_dict()

        # Instantiate GUI window
        self.gui = Window(
            gui_template=ui,
            host=socket.gethostbyname(socket.gethostname()),
            port=server_port
        )

        # Get Widgets
        self.widgets = get_gui_widgets(
            self.gui,
            DIO_table=1,
            update_DIO_button=1,
            channel_edit=1,
            pulse_type_combobox=1,
            add_channel_layout=1,
            add_pulse_layout=1
        )

        # Populate DIO table
        self.populate_dio_table_from_dict()

        # Connect "Update DIO Assignment" Button
        self.widgets['update_DIO_button'].clicked.connect(self.populate_dio_table_from_dict)

        # Initilize Pulse Selector Form
        self.setup_pulse_selector_form()

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

    def setup_pulse_selector_form(self):
        self.pulse_selector_form = QGroupBox("Pulse selector")
        self.pulse_selector_channelselection = QLineEdit()
        self.pulse_selector_pulse_drop_down = QComboBox()

        # Set selector.
        self.set_pulsetype_combobox()

        # Connect to change function
        self.pulse_selector_pulse_drop_down.currentTextChanged.connect(self.build_pulse_input_fields)

        layout = QFormLayout()
        layout.addRow(QLabel("Channel:"), QLineEdit())
        layout.addRow(QLabel("Pulse Type:"), QComboBox())
        self.pulse_selector_form.setLayout(layout)


    def build_pulse_input_fields(self):
        """Change input fields if pulse selector dropdown has been changed."""

        # Retrieve combobox-value
        current_pulsetype = str(self.widgets['pulse_type_combobox'].currentText())

        # Load pulsetype settings
        pulsetype_dict = [pulsedict for pulsedict in self.config_dict['pulse_types'] if pulsedict['name'] == current_pulsetype][0]

        # Clear all widgets containing pulse field inputs.
        for widget in self.widgets['add_pulse_layout'].children():
            widget.removeWidget()

        for field in pulsetype_dict['fields']:

            # Add a horizontal layout
            hbox = QHBoxLayout()

            # Add label.
            field_label = QLabel(field['label'])
            hbox.addWidget(field_label)

            # Build field.
            field_type = field['input_type']
            if field_type == 'QLineEdit':
                field_input = QLineEdit()
                hbox.addWidget(field_input)
            elif field_type == 'QComboBox':
                field_input = QComboBox()
                for choice in field['combo_choice']:
                    field_input.addItem(choice)

            # Add field to hbox.
            hbox.addWidget(field_input)

            # Add horizontal layout to.
            self.widgets['add_pulse_layout'].addLayout(hbox)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

    def set_pulsetype_combobox(self):
        for pulsetype in self.config_dict['pulse_types']:
            pulse_selector_pulse_drop_down.addItem(pulsetype['name'])

    def set_dio_channel_completer(self):
        """Reset the autocomplete for the channel selection."""
        completer = QCompleter(self.DIO_assignment_dict.keys())
        self.pulse_selector_channelselection.setCompleter(completer)

    def load_dio_assignment_from_dict(self):
        """Read in DIO assignment dictionary and store as member variable."""
        # Load DIO assignment.
        self.DIO_assignment_dict = load_config(
                config_filename=self.config_dict['DIO_dict'],
                logger=self.log
        )

    def populate_dio_table_from_dict(self):
        '''Populate DIO assignment table from DIO assignment dict.'''

        # Update DIO assignments from dict
        self.load_dio_assignment_from_dict()

        dio_table = self.widgets['DIO_table']

        # Define table size
        dio_table.setRowCount(len(self.DIO_assignment_dict.keys()))
        dio_table.setColumnCount(2)

        # Define header
        # header = QStandardItemModel()
        # header.setHorizontalHeaderLabels(['Staticline Name', 'DIO bit'])
        # dio_table.setModel(header)

        for i, (dio_name, dio_bit) in enumerate(self.DIO_assignment_dict.items()):
            #Populate it

            # Define table entries
            dio_name_item = QTableWidgetItem(str(dio_name))
            dio_bit_item = QTableWidgetItem(str(dio_bit))

            # Color entries
            dio_name_item.setForeground(QBrush(QColor(255, 255, 255)))
            dio_bit_item.setForeground(QBrush(QColor(255, 255, 255)))

            dio_table.setItem(i , 0, dio_name_item)
            dio_table.setItem(i , 1, dio_bit_item)

            # Update completer.
            self.set_dio_channel_completer()

            self.log.info('DIO settings successfully loaded.')

    def run(self):
        """ Runs an iteration of checks for updates and implements
        """

        time.sleep(0.01)
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
