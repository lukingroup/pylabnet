import pylabnet.utils.pulseblock.pulse as po
from pylabnet.utils.helper_methods import load_config
import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule
from pylabnet.hardware.staticline import staticline
from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import DIOPulseBlockHandler
from pylabnet.utils.helper_methods import slugify
import numpy as np



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

from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QGroupBox, QFormLayout, QErrorMessage, QComboBox, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout, QTableWidgetItem, QCompleter, QHBoxLayout, QLabel, QLineEdit


from PyQt5.QtGui import QBrush, QColor, QPainter, QItemDelegate
from PyQt5.QtCore import QRect, Qt, QAbstractTableModel
from PyQt5.QtCore import QVariant


class DictionaryTableModel(QAbstractTableModel):
    """ Table Model with data which can be access and set via a python dictionary."""
    def __init__(self, data, header, editable=False):
        """Instanciating  TableModel

        :data: Dictionary which should fill table,
            The key will be used to populate the first column entry,
            the item will be used to populate the subsequent columns.
            If item is String, only one column will be added. If Item is List,
            one new colum for every list item will be added.
        """
        super(DictionaryTableModel, self).__init__()

        # Prepare data.
        data_ok, datadict = self.__prepare_data(data)

        assert data_ok, "Input dictionary invalid."

        self.datadict = datadict
        self._header = header

        # Set editing mode.
        self.editable = editable

    def flags(self, index):
        """ Make table fields editable."""
        if self.editable:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.NoItemFlags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._header[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def _prepare_single_string_dict(self, datadict):
        """ Transform data dict into list of lists.

        To be used if dictionary values are strings.
        """

        data_list = []

        for key, item in datadict.items():
            data_list.append([key, item])


        if data_list == []:
            data_list = [["", ""]]

        return data_list

    def _prepare_list_dict(self, datadict):
        """ Transform data dict into list of lists.

        To be used if dictionary values are lists.
        TODO: Test this.
        """

        data_list = []

        for i, (key, item) in enumerate(datadict.items()):
            entry_list = []
            entry_list.append(key)
            for list_entry in item:
                entry_list.append(list_entry)

        return data_list

    def __prepare_data(self, datadict):
        """Check if dictioanry is either containing strings as values,
        or lists of the same length.

        Generate list out of dictionary.
        """

        values = datadict.values()
        data_ok = False

        # Check if all values are one allowed datatype:
        allowed_datatypes = [str, int, float]
        for allowed_datatype in allowed_datatypes:
            if all(isinstance(value, allowed_datatype) for value in values):
                data_ok = True
                datadict = self._prepare_single_string_dict(datadict)
                return data_ok, datadict

        # Check if values are all lists.
        if all(isinstance(value, list) for value in values):

            # Check if lists are of same length.
            it = iter(values)
            the_len = len(next(it))

            if not all(len(l) == the_len for l in it):
                data_ok = False
                return data_ok, None
            else:
                data_ok = True
                datadict = self._prepare_list_dict(datadict)
                return data_ok, datadict
        else:
            data_ok = False
            return data_ok, None

    def data(self, index, role):
        """ From https://stackoverflow.com/questions/28186118/how-to-make-qtableview-to-enter-the-editing-mode-only-on-double-click"""
        if not index.isValid(): return QVariant()
        row=index.row()
        column=index.column()

        if row>len(self.datadict): return QVariant()
        if column>len(self.datadict[row]): return QVariant()

        if role == Qt.EditRole or role == Qt.DisplayRole:
            return QVariant(self.datadict[row][column])

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        """ From https://stackoverflow.com/questions/28186118/how-to-make-qtableview-to-enter-the-editing-mode-only-on-double-click"""
        if index.isValid():
            if role == Qt.EditRole:
                row = index.row()
                column=index.column()
                if row>len(self.datadict) or column>len(self.datadict[row]):
                    return False
                else:
                    self.datadict[row][column]=value
                    self.dataChanged.emit(index, index)
                    return True
        return False

    def rowCount(self, index):
        # The length of the outer list.
        return len(self.datadict)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self.datadict[0])


    def add_dict(self, data_dict):
        """Populate table from dictionary.

        :data_dict: Dictionary to populate table from.
        """
        for i, (key, item) in enumerate(data_dict.items()):
            key = QTableWidgetItem(key)
            item = QTableWidgetItem(item)
            self.setItem(i,0,key)
            self.setItem(i,1,str(item))


class AddPulseblockPopup(QWidget):
    """ Widget class of Add pulseblock popup"""
    def __init__(self):
        QWidget.__init__(self)

        self.pulseblock_name_field = None
        self.pulseblock_inherit_field = None
        self.form_layout = None
        self.form_groupbox = None
        self.global_hbox = None

    def return_pulseblock_new_pulseblock(self):
        """ Add new pulseblock by clicking the "Add Pb" button."""

        # Get pulseblock name
        pb_name = self.pulseblock_name_field.text()
        pulseblock= pb.PulseBlock(name=pb_name)

        return pb_name, pulseblock


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
            add_pulse_layout=1,
            add_pulse_button=1,
            new_pulseblock_button=1,
            pulseblock_combo=1,
            variable_table_view = 1,
            add_variable_button = 1,
            pulse_scrollbox = 1
        )

        # Initialize empty pulseblock dictionary.
        self.pulseblocks = {}

        # Initialize Variable dict
        self.vars = {}

        self.variable_table =self.widgets['variable_table_view']

        self.variable_table_model = DictionaryTableModel(
            self.vars,
            header=["Variable", "Value"],
            editable=True
        )

        self.variable_table.setModel(self.variable_table_model)

        # Connect change of vartiable data to update variable dict function.
        self.variable_table_model.dataChanged.connect(self._update_variable_dict)

        # Store completers
        self.var_completer  = QCompleter(self.vars.keys())

        # Connect Add variable button.
        self.widgets['add_variable_button'].clicked.connect(self._add_row_to_var_table)


        # Connect "Update DIO Assignment" Button
        self.widgets['update_DIO_button'].clicked.connect(self.populate_dio_table_from_dict)


        # Store widget which store variable autocomplete.
        self.var_completer_widgets = []

        # Initilize Pulse Selector Form
        self.setup_pulse_selector_form()

         # Populate DIO table
        self.populate_dio_table_from_dict()


        # Connect add pulse button.
        self.widgets['add_pulse_button'].clicked.connect(self.add_pulse_from_form)
        self.widgets['new_pulseblock_button'].clicked.connect(self.add_pulseblock)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()


        # Make pulse toolbox invisible
        self.widgets['pulse_scrollbox'].hide()


        self.add_pb_popup = None

    def validate_and_clean_vars_data(self, table_data):
        """Validate and typecast variable table data"""

        validated = True

        for row in table_data:
            varname = row[0]
            var_val = row[1:][0]
            if varname == "":
                validated = False
                self.log.warn(f'Variable name {varname} is valid.')

            # Try typecast
            try:
                # Typecast and update data.
                var_val_float = float(var_val)
            except ValueError:
                self.log.warn(f'Variable value {var_val} cannot be typecast to float.')
                validated =  False

        return validated, table_data

    def _update_variable_dict(self):
        """ Get variables from table and store in dict."""
        table_data = np.asarray(self.variable_table_model.datadict)

        # If data are not valid, do nothing.
        validated, cleaned_data = self.validate_and_clean_vars_data(table_data)
        if not validated:
            return

        # Reset variable dict:
        self.vars = {}

        # Update data
        for row in cleaned_data:
            self.vars[row[0]] = float(row[1:][0])

        # Update completer
        self.update_var_completer()

    def _add_row_to_var_table(self):
        self.variable_table_model.datadict.append(["", ""])
        self.variable_table_model.layoutChanged.emit()

    def add_pulseblock(self):
        self.add_pb_popup = AddPulseblockPopup()
        self.add_pb_popup.setObjectName('add_pb_popup')
        self.add_pb_popup.setGeometry(QRect(100, 100, 400, 200))

        self.add_pb_popup.global_hbox = QVBoxLayout()
        self.add_pb_popup.setLayout(self.add_pb_popup.global_hbox)


        # Setup of box.
        self.add_pb_popup.form_groupbox = QGroupBox("Add Pulseblock")
        self.add_pb_popup.form_layout = QFormLayout()


        self.add_pb_popup.pulseblock_name_field = QLineEdit()
        self.add_pb_popup.pulseblock_inherit_field = QComboBox()

        # Add pulseblock choices.
        self.add_pb_popup.pulseblock_inherit_field.addItems(self.get_pulseblock_names())


        # Create one Form to contain the for fields that never change.
        self.add_pb_popup.form_layout.addRow(QLabel("Pulseblock Name:"), self.add_pb_popup.pulseblock_name_field)
        self.add_pb_popup.form_layout.addRow(QLabel("Inherit from:"), self.add_pb_popup.pulseblock_inherit_field)
        self.add_pb_popup.form_groupbox.setLayout(self.add_pb_popup.form_layout)

        # Set Layout
        self.add_pb_popup.setLayout(self.add_pb_popup.form_layout)

        # Add to global hbox
        self.add_pb_popup.global_hbox.addWidget(self.add_pb_popup.form_groupbox)

        # Add button
        add_pb_button = QPushButton('Add Pulseblock')
        add_pb_button.setObjectName("add_pb_button")
        self.add_pb_popup.global_hbox.addWidget(add_pb_button)

        # Connect Button to add pulseblock function
        add_pb_button.clicked.connect(self.add_pulseblock_from_popup)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

        # Shot the pop-up
        self.add_pb_popup.show()

    def update_pulseblock_dropdown(self):
        """Update pulseblock dropdown"""

        self.widgets['pulseblock_combo'].clear()
        self.widgets['pulseblock_combo'].addItems(self.get_pulseblock_names())

    def get_pulseblock_names(self):
        return self.pulseblocks.keys()


    def add_pulseblock_from_popup(self):
        """Create new pulseblock instance and add to pb dictionary"""

        # Get pulseblocks from Popup class
        pb_name, pulseblock = self.add_pb_popup.return_pulseblock_new_pulseblock()

        # Add pulseblock
        self.pulseblocks[pb_name] = pulseblock

        # Update pulseblock dropdown.
        self.update_pulseblock_dropdown()

        # Close popup
        self.add_pb_popup.close()


    def add_pulse_from_form(self):
        """Get pulse info from form, create Pulse object and add to pulse list"""

        # Retrieve pulse:
        new_pulsetype = str(self.pulse_selector_pulse_drop_down.currentText())

        # Get pulsetype dict
        pulsetype_dict = self._current_pulsetype_dict()

        valid, pulsedict = self.read_pulse_params_from_form()

        if not valid:
            return

        # # Create new pulse
        if pulsetype_dict["pulseblock_type"] == "PTrue":
            new_pulse = po.PTrue(
                ch=pulsedict["channel"],
                dur=pulsedict["dur"]
            )
        elif pulsetype_dict["pulseblock_type"] == "PSin":
            new_pulse = po.PSin(
                ch=pulsedict["channel"],
                dur=pulsedict["dur"],
                amp=pulsedict["amp"],
                freq=pulsedict["freq"],
                ph=pulsedict["ph"]
            )

        self.showerror(str(new_pulse))



    def return_pulsedict(self, pulsetype_dict):
        """ Return values of pulse fields."""

        # Retreive values
        qline__field_names =   [self._get_form_field_widget_name(field) for field in pulsetype_dict['fields'] if field['input_type'] == "QLineEdit"]
        combobox_field_names = [self._get_form_field_widget_name(field) for field in pulsetype_dict['fields'] if field['input_type'] == "QComboBox"]

        qline__field_vars =   [field['var'] for field in pulsetype_dict['fields'] if field['input_type'] == "QLineEdit"]
        combobox_field_vars = [field['var'] for field in pulsetype_dict['fields'] if field['input_type'] == "QComboBox"]

        qlineedits = [self.pulse_selector_form_variable.findChild(QLineEdit, field_name).text() for field_name in qline__field_names ]
        comboboxs =  [self.pulse_selector_form_variable.findChild(QComboBox, field_name).currentText() for field_name in combobox_field_names]


        # Construc data
        pulsedict_data = {}
        for field_name, field_val in zip(qline__field_vars, qlineedits):
            pulsedict_data[field_name] = field_val

        for field_name, field_val in zip(combobox_field_vars, comboboxs):
            pulsedict_data[field_name] = field_val

        return pulsedict_data


    def clean_and_validate_pulsedict(self, pulsedict):
        """ Check if input values are valid and typecast values"""
        validated = True
        typecast_error = []
        for key, val in pulsedict.items():
            try:
                # Typecast and update data.
                var_val_float = float(val)
                pulsedict[key] = var_val_float
            except ValueError:
                # if typecasting failed, check value is variable.
                if val not in self.vars.keys() and key != "tref":
                    typecast_error.append(key)
                    validated =  False

        if not validated:
            if len(typecast_error) > 1:
                error_msg = f"Invalid entries for parameters: {typecast_error}"
            else:
                error_msg = f"Invalid entry for parameter {typecast_error[0]}"
            self.showerror(error_msg)

        return validated, pulsedict

    def read_pulse_params_from_form(self):
        """ Read pulse parameters from input form, perfomr
        integrity check and return a check flag as well as a dictioanry.
        """

        channel = self.pulse_selector_channelselection.text()
        if channel not in self.DIO_assignment_dict.keys():
            self.showerror("Please provide valid channel name.")
            channel_validated = False
        else:
            channel_validated = True

        # Get data from fields
        if channel_validated:
            pulsetype_dict = self._current_pulsetype_dict()
            pulsedict_data = self.return_pulsedict(pulsetype_dict)

            # Validate data
            data_validated, pulsedict = self.clean_and_validate_pulsedict(pulsedict_data)

            # Add channel to dict
            pulsedict['channel'] = channel
        else:
            data_validated = False
            pulsedict = None

        if  data_validated and channel_validated:
            valid = True
        else:
            valid = False

        return valid, pulsedict


    def showerror(self, error_message):
        """ Show error message."""
        error_dialog = QErrorMessage()
        error_dialog.showMessage(error_message)
        error_dialog.exec_()


    def update_var_completer(self):
        """ Update variable completer """
        self.var_completer  = QCompleter(self.vars.keys())

        for widget in self.var_completer_widgets:
                widget.setCompleter(self.var_completer)


    def setup_pulse_selector_form(self):
        self.pulse_selector_form_static = QGroupBox()
        self.pulse_selector_form_static.setObjectName("pulse_static_input")
        self.pulse_selector_channelselection = QLineEdit()
        self.pulse_selector_pulse_drop_down = QComboBox()

        # Set selector.
        self.set_pulsetype_combobox()

        # Connect to change function
        self.pulse_selector_pulse_drop_down.currentTextChanged.connect(self.build_pulse_input_fields)

        # Create one Form to contain the for fields that never change.
        self.pulse_selector_form_layout_static = QFormLayout()
        self.pulse_selector_form_layout_static.addRow(QLabel("Channel:"), self.pulse_selector_channelselection)
        self.pulse_selector_form_layout_static.addRow(QLabel("Pulse Type:"), self.pulse_selector_pulse_drop_down)
        self.pulse_selector_form_static.setLayout(self.pulse_selector_form_layout_static)


        # Add a second form containing the fields that change from pulsetype to pulsetype
        self.pulse_selector_form_variable = QGroupBox()
        self.pulse_selector_form_variable.setObjectName("pulse_var_input")

        self.pulse_selector_form_layout_variable = QFormLayout()
        self.pulse_selector_form_variable.setLayout(self.pulse_selector_form_layout_variable)

        # Add forms to Hbox layout
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_static)
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_variable)

        # Build pulse-specific fileds.
        self.build_pulse_input_fields()

    def _remove_variable_pulse_fields(self):
        """Remove all pulse-type specific fields from layout."""
        num_rows =  self.pulse_selector_form_layout_variable.rowCount()
        for _ in range(num_rows):
            self.pulse_selector_form_layout_variable.removeRow(0)


    def _get_current_pulsetype(self):
        """Get selected pulsetype from form."""
        return str(self.pulse_selector_pulse_drop_down.currentText())

    def _get_pulsetype_dict(self, current_pulsetype):
        """ Return dictionary of pulsetype"""
        pulsetype_dict = [pulsedict for pulsedict in self.config_dict['pulse_types'] if pulsedict['name'] == current_pulsetype][0]
        return pulsetype_dict

    def _current_pulsetype_dict(self):
        """Get DIctionary of durrently selected pulsetype"""
        return self._get_pulsetype_dict(self._get_current_pulsetype())


    def _get_form_field_widget_name(self, field_dict):
        """Generates a unique name for pulse add form fields."""
        field_input = self._get_pulse_fieldtype(field_dict)
        field_input_str = str(type(field_input)).replace("<class 'PyQt5.QtWidgets.", "").replace("'>", "")
        input_widget_name = f"{slugify(field_dict['label'])}_{str(field_input_str)}"
        return input_widget_name


    def _get_pulse_fieldtype(self, field_dict):
        """Determie input field type."""
        # Build field.
        field_type = field_dict['input_type']
        if field_type == 'QLineEdit':
            field_input = QLineEdit()
        elif field_type == 'QComboBox':
            field_input = QComboBox()
        return field_input

    def build_pulse_input_fields(self):
        """Change input fields if pulse selector dropdown has been changed."""

        # Remove old entries.
        self._remove_variable_pulse_fields()

        # Resset widget list
        self.var_completer_widgets = []

        # Load pulsetype settings
        pulsetype_dict = self._current_pulsetype_dict()

        for field in pulsetype_dict['fields']:

            # Add label.
            field_label = QLabel(field['label'])

            # Get field type
            field_input = self._get_pulse_fieldtype(field)

            # Add choices to combobox.
            if type(field_input) is QComboBox:
                    field_input.addItems(field['combo_choice'])
            else:
                # Add completer
                self.var_completer_widgets.append(field_input)
                field_input.setCompleter(self.var_completer)

            # Auto create name of widget:
            input_widget_name = self._get_form_field_widget_name(field)
            field_input.setObjectName(input_widget_name)

            self.pulse_selector_form_layout_variable.addRow(field_label, field_input)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()


    def set_pulsetype_combobox(self):
        for pulsetype in self.config_dict['pulse_types']:
            self.pulse_selector_pulse_drop_down.addItem(pulsetype['name'])

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

        self.model = DictionaryTableModel(self.DIO_assignment_dict, header=["Channel Name", "DIO Bit"])
        self.widgets['DIO_table'].setModel(self.model)

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
