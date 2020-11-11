
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, get_gui_widgets
from pylabnet.gui.pyqt.external_gui import Window

import socket
import time
import numpy as np


class TopticaFilterWheelController:
    """ Class for controlling Toptica scan and laser properties """

    def __init__(self, filterwheel1, filterwheel2, gui='toptica_filterwheels', logger=None, port=None):


        self.filterwheel1 = filterwheel1
        self.filterwheel2 = filterwheel2

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

        # Retrieve filter dicts.
        filters1 = filterwheel1.get_filter_dict()
        filters2 = filterwheel2.get_filter_dict()

        # Fill comboboxes.
        self.widgets['comboBox_filter1'].addItems(filters1.values())
        self.widgets['comboBox_filter2'].addItems(filters2.values())

        # Get current fitler positions
        self.current_pos_1 = filterwheel1.get_pos()
        self.current_pos_2 = filterwheel2.get_pos()

        # Set comboboxes to current filter positions.
        self.widgets['comboBox_filter1'].setCurrentIndex(int(self.current_pos_1)-1)
        self.widgets['comboBox_filter2'].setCurrentIndex(int(self.current_pos_2)-1)

        # Connect change events
        self.widgets['comboBox_filter1'].currentTextChanged.connect(lambda : self.change_filter(filter_index=1))
        self.widgets['comboBox_filter2'].currentTextChanged.connect(lambda:  self.change_filter(filter_index=2))

        # Update OD reading
        self.update_od()

        # Setup stylesheet.
        self.gui.apply_stylesheet()

    def change_filter(self, filter_index):
        ''' Read in index from combobox and change filter accordingly.'''
        # Read in new filter.
        new_pos = int(self.widgets[f'comboBox_filter{filter_index}'].currentIndex())+1

        if filter_index == 1:
            filterwheel = self.filterwheel1
        elif filter_index == 2:
            filterwheel = self.filterwheel2

        # Disable comboboxes
        self.widgets['comboBox_filter1'].setEnabled(False)
        self.widgets['comboBox_filter2'].setEnabled(False)

        # Change position
        successful_changed = filterwheel.change_filter(new_pos)

        if not successful_changed:
            # Read in new position to verify
            changed_position = filterwheel.get_pos()

            # Set combobox to new position
            self.widgets[f'comboBox_filter{filter_index}'].setCurrentIndex(int(changed_position)-1)

        # Update OD reading
        self.update_od()

        # Enable combobos
        self.widgets['comboBox_filter1'].setEnabled(True)
        self.widgets['comboBox_filter2'].setEnabled(True)

    def update_od(self):

        filter_pos1 = int(self.widgets['comboBox_filter1'].currentIndex())+1
        filter_string1 = self.filterwheel1.get_filter_dict()[str(filter_pos1)]
        filter1_od = float(filter_string1.replace(' OD', ""))

        filter_pos2 = int(self.widgets['comboBox_filter2'].currentIndex())+1
        filter_string2 = self.filterwheel2.get_filter_dict()[str(filter_pos2)]
        filter2_od = float(filter_string2.replace(' OD', ""))

        new_od_string = f"{filter1_od+filter2_od} OD"

        self.widgets['nd_label'].setText(new_od_string)

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


