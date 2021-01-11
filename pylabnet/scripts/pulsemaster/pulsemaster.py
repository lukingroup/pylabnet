
import copy
import numpy as np
import time
import pyqtgraph as pg
import json
import socket
import functools

from PyQt5.QtWidgets import QShortcut,  QToolBox, QFileDialog,  QMessageBox, QPushButton, QGroupBox, QFormLayout, QComboBox, QWidget, QTableWidgetItem,QVBoxLayout, QTableWidgetItem, QCompleter, QLabel, QLineEdit
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import QRect, Qt, QAbstractTableModel
from PyQt5.QtCore import QVariant

from simpleeval import simple_eval, NameNotDefined

import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.hardware.awg.zi_hdawg import Driver
from pylabnet.utils.helper_methods import slugify
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import unpack_launcher, load_config, load_script_config, get_gui_widgets
from pylabnet.utils.pulsed_experiments.pulsed_experiment import PulsedExperiment

from pylabnet.scripts.pulsemaster.pulseblock_constructor import PulseblockConstructor, PulseSpecifier
from pylabnet.scripts.pulsemaster.pulsemaster_customwidget import DictionaryTableModel, AddPulseblockPopup


class PulseMaster:

    # Generate all widget instances for the .ui to use
    # _plot_widgets, _legend_widgets, _number_widgets = generate_widgets()

    def __init__(self, config, ui='pulsemaster', logger_client=None, server_port=None):
        """ TODO
        """

        self.log = logger_client

        # Load config dict.
        self.config_dict = load_script_config(
            script='pulsemaster',
            config=config,
            logger=self.log
        )

        # Instanciate HD
        dev_id = self.config_dict['HDAWG_dev_id']
        self.hd = Driver(dev_id, logger=self.log)

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
            pulse_list_vlayout=1,
            pulse_scrollarea=1,
            pulse_layout_widget=1,
            seq_var_table=1,
            load_seq_vars= 1,
            save_seq_vars=1,
            seqt_textedit=1,
            load_seqt=1,
            save_seqt=1,
            start_hdawg=1,
            stop_hdawg=1,
            autostart=1,
            upload_hdawg=1,
            awg_num_val=1,
            preview_seq_area=1,
            save_pulseblock=1,
            load_pulseblock=1
        )

        # Initialize empty pulseblock dictionary.
        self.pulseblocks = {}


        # Initialize empty dictionary containing the contruction
        # Instructions for the currently displayed pulseblock.
        self.pulseblock_constructors = []

        # Initialize Variable dict
        self.vars = {}

        self.variable_table =self.widgets['variable_table_view']

        self.variable_table_model = DictionaryTableModel(
            self.vars,
            header=["Variable", "Value"],
            editable=True
        )

        self.variable_table.setModel(self.variable_table_model)

        # Store completers
        self.var_completer  = QCompleter(self.vars.keys())

        # Initilize Pulse Selector Form
        self.setup_pulse_selector_form()

         # Populate DIO table
        self.populate_dio_table_from_dict()

        self.pulse_toolbox = QToolBox()

        # Make pulse toolbox invisible
        #self.widgets['pulse_toolbox'].hide()
        self.widgets['pulse_scrollarea'].setWidget(self.pulse_toolbox)


        # Initilize sequencer table
        self.seq_var_dict = {}

        # Initialize Sequencer Variable table.
        self.seq_var_table = self.widgets['seq_var_table']

        self.seq_variable_table_model = DictionaryTableModel(
            self.seq_var_dict,
            header=["Sequence Variable", "Value"],
            editable=True
        )

        self.seq_var_table.setModel(self.seq_variable_table_model)

        self.add_pb_popup = None

         # Apply CSS stylesheet
        self.gui.apply_stylesheet()

        # Assign all actions to buttons and data-change events
        self.assign_actions()

        # Apply all custom styles
        self.apply_custom_styles()

        self.awg_running = False

    def apply_custom_styles(self):
        """Apply all style changes which are not specified in the .css file."""

        # Set background of custom PoltWidgets
        self.widgets["pulse_layout_widget"].getViewBox().setBackgroundColor('#19232D')
        self.widgets["pulse_layout_widget"].setBackground('#19232D')

        # Color HDAWG buttons.
        self.widgets["stop_hdawg"].setStyleSheet("background-color : #6a040f")
        self.widgets["start_hdawg"].setStyleSheet("background-color : #006d77")

    def assign_actions(self):
        """Perform all button of data-changed connections in here."""

        # Connect load and save sequence template buttons.
        self.widgets["load_seqt"].clicked.connect(self.load_sequence_template)
        self.widgets["save_seqt"].clicked.connect(self.save_sequence_template)

        # Connect Load Sequencer Button
        self.widgets["load_seq_vars"].clicked.connect(self.get_seq_var_dict_from_file)
        self.widgets["save_seq_vars"].clicked.connect(self.save_seq_variables_dict)

        # Connect add pulse button.
        self.widgets['add_pulse_button'].clicked.connect(self.add_pulse_from_form)
        self.widgets['new_pulseblock_button'].clicked.connect(self.add_pulseblock)

        # Connect pulseblock selector object
        self.widgets["pulseblock_combo"].currentIndexChanged.connect(self.pulseblock_dropdown_changed)

        # Connect Add variable button.
        self.widgets['add_variable_button'].clicked.connect(self._add_row_to_var_table)

        # Connect "Update DIO Assignment" Button
        self.widgets['update_DIO_button'].clicked.connect(self.populate_dio_table_from_dict)

        # Connect change of variable data to update variable dict function.
        self.variable_table_model.dataChanged.connect(self._update_variable_dict)

        # Connect HDAWG buttons
        self.widgets["stop_hdawg"].clicked.connect(self.stop_hdawg)
        self.widgets["start_hdawg"].clicked.connect(self.start_hdawg)
        self.widgets["upload_hdawg"].clicked.connect(self.upload_hdawg)

        # Connect ctr+enter to upload AWG
        self.msgSc1 = QShortcut(QKeySequence('Ctrl+Return'), self.gui)
        self.msgSc2 = QShortcut(QKeySequence('Ctrl+Enter'), self.gui)
        self.msgSc1.activated.connect(self.upload_hdawg)
        self.msgSc2.activated.connect(self.upload_hdawg)

        #Save Pulseblock Button
        self.widgets["save_pulseblock"].clicked.connect(self.save_current_pb_constructor)
        self.widgets["load_pulseblock"].clicked.connect(self.load_pulseblock_from_file)


    def pulseblock_dropdown_changed(self):
        self.update_pulse_list_toolbox()
        self.plot_current_pulseblock()

    def get_pb_specifier_from_dict(self, pulsedict):
        """ Create PulseSpecifier object from dictioanry."""

        pb_specifier = PulseSpecifier(
            channel = pulsedict['channel'],
            pulsetype = pulsedict['pulsetype'],
            pulsetype_name = pulsedict['name']
        )

        pb_specifier.set_timing_info(
            offset = pulsedict['offset'],
            dur = pulsedict['dur'],
            tref = pulsedict['tref']
        )

        pb_specifier.set_pulse_params(
            pulsevar_dict = pulsedict['pulse_vars']
        )

        return pb_specifier


    def get_pb_constructor_from_dict(self, pb_dict):
        """Generate Pb contructor from dictionary."""

        try:

            new_var_dict = pb_dict['var_dict']

            # Update variable dict
            self.vars.update(new_var_dict)

            pb_constructor = PulseblockConstructor(
                name=pb_dict['name'],
                log=self.log,
                var_dict=new_var_dict
            )

            for pulsedict in pb_dict['pulse_specifiers_dicts']:
                new_pb_specifier = self.get_pb_specifier_from_dict(pulsedict)
                pb_constructor.pulse_specifiers.append(new_pb_specifier)

        except KeyError as e:
            self.showerror(f"Invalid pulse sequence JSON file (KeyError for attribute {e}).")

        return pb_constructor

    def load_pulseblock_from_file(self):
        """ Load PB constructor from file"""

        # Get filename from pop-up.
        pb_dict = self.load_json_dict()

        # Create pulseblock contructor.
        imported_contructor = self.get_pb_constructor_from_dict(pb_dict)

        # Check if pulseblock with same name alraedy exists
        if  imported_contructor.name in [constructor.name for constructor in self.pulseblock_constructors]:
            self.showerror(f"There already exists a pulseblock with the name '{imported_contructor.name}'.")
            return

        # Append to contructor.
        self.pulseblock_constructors.append(imported_contructor)

        #Temporarliy disconnect the currentIndexChanged so it does not fire during the
        # constructor generation
        self.widgets["pulseblock_combo"].currentIndexChanged.disconnect()

        # Update pulseblock dropdown.
        self.update_pulseblock_dropdown()

        self.widgets["pulseblock_combo"].currentIndexChanged.connect(self.pulseblock_dropdown_changed)

        # Select newest Pb.
        self.widgets["pulseblock_combo"].setCurrentText(imported_contructor.name)
        self.plot_current_pulseblock()

        # TODO find out how to update table without re-instanciation.
        # Update Variable table.
        self.variable_table_model = DictionaryTableModel(
            self.vars,
            header=["Variable", "Value"],
            editable=True
        )

        self.variable_table.setModel(self.variable_table_model)

        # Connect change of variable data to update variable dict function.
        self.variable_table_model.dataChanged.connect(self._update_variable_dict)

        # Update Toolbox.
        self.update_pulse_list_toolbox()

    def save_current_pb_constructor(self):
        """ Save current Pulseblock constructor as .json file"""

        current_pb = self.get_current_pb_constructor()
        current_pb_dict = current_pb.get_dict()

        # Save as JSON file.
        self.json_file_save(current_pb_dict)

    def start_hdawg(self):
        """Start the AWG core."""
        self.awg.start()
        self.awg_running = True

    def stop_hdawg(self):
        """Stop the AWG core."""
        self.awg.stop()
        self.awg_running = False

    def upload_hdawg(self):
        """ Embedd current pulseblock in sequence template and
        upload to HDAWG.
        """

        # Stop AWG if it's running.
        if self.awg_running:
            self.stop_hdawg()

        #Compile pulseblock.
        self.compile_current_pulseblock()

        # Retrieve compiled pulseblock.
        pulseblock = self.get_current_pb_constructor().pulseblock

        # Get sequence template from textbox.
        seq_template = self.widgets['seqt_textedit'].toPlainText()
        if seq_template == "":
            self.showerror('No sequence template defined.')
            return

        # Retrieve AWG number from settings.
        awg_num = self.widgets['awg_num_val'].value()

        # Retrieve placeholder dictionary from table.
        placeholder_dict = self.get_seq_var_dict()

        self.pulsed_experiment = PulsedExperiment(
            pulseblocks=pulseblock,
            placeholder_dict=placeholder_dict,
            assignment_dict=self.DIO_assignment_dict ,
            hd=self.hd,
            use_template=False,
            sequence_string=seq_template,
            iplot=False
        )

        # Upload to HDAWG
        self.awg = self.pulsed_experiment.get_ready(awg_num)

        # Retrieve uploaded sequence
        uploaded_sequence = self.pulsed_experiment.seq.sequence

        # Set sequence previewer.
        self.widgets['preview_seq_area'].setText(uploaded_sequence)

        # Upload sequence to metadata
        self.log.update_metadata(
            pulseblock_constructor=self.get_current_pb_constructor().get_dict()
        )

        # If the Autostart check is true, start the HDAWG
        if self.widgets['autostart'].isChecked():
            self.start_hdawg()

    def save_sequence_template(self):
        """Save a sequence template from a file."""
        current_seq_template = self.widgets['seqt_textedit'].toPlainText()
        self.text_filesave(data=current_seq_template)

    def load_sequence_template(self):
        """Load a sequence template from a file."""
        seq_temp_filename = self.get_filename(filetype="Sequencer-template files (*.seqct)")

        # Open seqct file and store sequence template as member variable.
        f = open(seq_temp_filename[0], "r")
        self.seq_temp = f.read()

        # Set value to textbox.
        self.widgets['seqt_textedit'].setText(self.seq_temp)
        self.widgets['seqt_textedit'].selectAll()
        self.widgets['seqt_textedit'].setFontPointSize(10)

        # Unselect
        cursor = self.widgets['seqt_textedit'].textCursor()
        cursor.clearSelection()
        self.widgets['seqt_textedit'].setTextCursor(cursor)


    def text_filesave(self, data, filetype="Sequencer-template files (*.seqct)"):
        """ Generic text file save."""
        name = QFileDialog.getSaveFileName( self.gui, 'Save File', '', filetype)
        with open(name[0], "w") as text_file:
            text_file.write(data)

    def json_file_save(self, data):
        """ Generic file saving."""
        name = QFileDialog.getSaveFileName( self.gui, 'Save File', '', "JSON files (*.json)")
        with open(name[0],'w') as fp:
            json.dump(data, fp, indent=4)

        self.log.info(f"Successfully saved data as {name[0]}")

    def save_seq_variables_dict(self):
        """Save sequencer variables in file."""

        # Get Data
        data = self.get_seq_var_dict()



        self.json_file_save(data)

    def get_seq_var_dict(self):
        """ Read new sequencer variables from the table,
        """
        return dict(self.seq_variable_table_model.datadict)

    def get_seq_var_dict_from_file(self):
        """ Load assignment dictionary from file."""

        # Get filepath from file-sepector popup.
        seq_var_dict = self.load_json_dict()

        # Retrieve sub-dictionary
        seq_var_dict = seq_var_dict['sequence_vars']

        self.seq_var_dict = seq_var_dict

        # Initialize Sequencer Variable table.
        self.seq_var_table = self.widgets['seq_var_table']

        self.seq_variable_table_model = DictionaryTableModel(
            self.seq_var_dict,
            header=["Variable", "Value"],
            editable=True
        )

        self.seq_var_table.setModel(self.seq_variable_table_model)


    def get_filename(self, filetype="JSON files (*.json)"):
        """Open file selector widget and get files."""
        return QFileDialog.getOpenFileName(self.gui, 'Open file', '',filetype)

    def load_json_dict(self):
        """Open pop-up, search for JSON file and return as dict."""

        filename = self.get_filename()

        f = open(filename[0])

        # returns JSON object as
        # a dictionary
        dictionary = json.load(f)

        return dictionary

    def prep_plotdata(self, pb_obj):

        self.widgets["pulse_layout_widget"].clear()

        # Iterate through p_dict.keys() and dflt_dict.keys()
        # and create a trace for each channel
        #  - create sorted list of channels
        d_ch_set = set(pb_obj.dflt_dict.keys())
        p_ch_set = set(pb_obj.p_dict.keys())
        ch_list = list(d_ch_set | p_ch_set)
        ch_list.sort()

        # - iterate trough ch_list
        trace_list = []
        for ch_index, ch in enumerate(ch_list):

            #
            # Build x_ar, y_ar, text_ar
            #

            # initial zero-point - default pulse object printout
            x_ar = [0]
            y_ar = [ch_index]
            if ch in pb_obj.dflt_dict.keys():
                text_ar = [
                    '{}'.format(
                        str(pb_obj.dflt_dict[ch])
                    )
                ]
            else:
                text_ar = ['']

            # Iterate through pulse list and create a rectangular
            # arc for each pulse. The mid-point on the upper segment
            # contains printout of the pulse object
            if ch in pb_obj.p_dict.keys():
                for p_item in pb_obj.p_dict[ch]:
                    # edges of the pulse
                    t1 = p_item.t0
                    t2 = p_item.t0 + p_item.dur

                    # left vertical line
                    if t1 == 0:
                        # If pulse starts at the origin,
                        # do not overwrite (x=0, y=ch_index) point
                        # which contains dflt_dict[ch] printout
                        x_ar.append(t1)
                        y_ar.append(ch_index + 0.8)
                    else:
                        x_ar.extend([t1, t1])
                        y_ar.extend([ch_index, ch_index + 0.8])

                    # mid-point, which will contain printout
                    x_ar.append((t1 + t2) / 2)
                    y_ar.append(ch_index + 0.8)

                    # right vertical line
                    x_ar.extend([t2, t2])
                    y_ar.extend([ch_index + 0.8, ch_index])

                    # set mid-point text to object printout
                    if t1 == 0:
                        # If pulse starts at the origin,
                        # do not overwrite (x=0, y=ch_index) point
                        # which contains dflt_dict[ch] printout
                        text_ar.extend(
                            [
                                '{:.2e}'.format(t1),
                                '{}'.format(str(p_item)),
                                '{:.2e}'.format(t2),
                                '{:.2e}'.format(t2)
                            ]
                        )
                    else:
                        text_ar.extend(
                            [
                                '{:.2e}'.format(t1),
                                '{:.2e}'.format(t1),
                                '{}'.format(str(p_item)),
                                '{:.2e}'.format(t2),
                                '{:.2e}'.format(t2)
                            ]
                        )

            # final zero-point
            x_ar.append(pb_obj.dur)
            y_ar.append(ch_index)
            text_ar.append('{:.2e}'.format(pb_obj.dur))

            pen=pg.mkPen(
               color=self.gui.COLOR_LIST[
                ch_index
            ],
            width=3
            )
            self.widgets["pulse_layout_widget"].addLegend()
            self.widgets["pulse_layout_widget"].plot(x_ar, y_ar, pen=pen, name=ch)

    def compile_current_pulseblock(self, update_variables=True):
        """Compile the current pulseblock

        :update_variables: If True, update variables.
        """

        # Retrieve current pulseblcok contructor.
        pb_constructor = self.get_current_pb_constructor()

        # Do nothing if no constructor found.
        if pb_constructor == None:
            return

        # Update variables.
        if update_variables:
            self._update_variable_dict()

        # Update variable dict
        pb_constructor.var_dict = self.vars

        # try to compile the pulseblock
        try:
            pb_constructor.compile_pulseblock()
            compliation_successful= True
            self.log.info(f"Succesfully compiled pulseblock {pb_constructor.name}.")
        except ValueError as e:
            self.showerror(str(e))
            compliation_successful = False

        return compliation_successful

    def plot_current_pulseblock(self, update_variables=True):

        # Compile pulseblock
        if not self.compile_current_pulseblock(update_variables):
            return

        self.prep_plotdata(self.get_current_pb_constructor().pulseblock)

    def copy_pulseblock_constructor(self, pb_constructor, new_name):
        """ Generate new instance of pulseblock constructor which is identical to reference instance,
        with the excpetion of the name.

        :pb_constructor: PulseblockCOntructor object to be copied.
        :new_name: New name of copied instance.
        """

        # Retrieve pulseblock contructor dictionary from old constructor.
        pb_constructor_dict = pb_constructor.get_dict()

        # Generate copy of constructor using the dictionary.
        copied_constructor = self.get_pb_constructor_from_dict(pb_constructor_dict)

        # Replace name of copy.
        copied_constructor.name = new_name

        return copied_constructor

    def  return_pulseblock_new_pulseblock_constructor(self):
        """ Add new pulseblock by clicking the "Add Pb" button."""

        inherit_combobox_text = self.add_pb_popup.pulseblock_inherit_field.currentText()
        pb_name = self.add_pb_popup.pulseblock_name_field.text()

        # If no option is choosen in the dropdown, generate new pb contructor.
        if inherit_combobox_text == "":
            pb_constructor= PulseblockConstructor(
                name=pb_name,
                log=self.log,
                var_dict = self.vars
            )

        # Otherwise copy and rename constructor.
        else:
            ref_pb_constructor = self.get_pb_contructor_by_name(inherit_combobox_text)
            pb_constructor = self.copy_pulseblock_constructor(
                pb_constructor = ref_pb_constructor,
                new_name = pb_name
            )

        return pb_constructor


    def update_pulse_list_toolbox(self):
        """Read in PulseblockContructor of currently selected Pulseblock
        and display it in the pulse-list toolbox."""

        current_pb_constructor = self.get_current_pb_constructor()

        # Close previous Toolbox.
        if self.pulse_toolbox is not None:
            self.pulse_toolbox.close()

        self.pulse_toolbox = QToolBox()

        # Add Toolbox to layout
        self.widgets["pulse_scrollarea"].setWidget(self.pulse_toolbox)

        # If no pulses are added, keep toolbox hidden.
        if len(current_pb_constructor.pulse_specifiers) == 0:
            return

        # Add new Entries.
        for i, pulse_specifier in enumerate(current_pb_constructor.pulse_specifiers):
            pulse_form, pulse_layout = self.get_pulse_specifier_form(
                pulse_specifier=pulse_specifier,
                pb_constructor=current_pb_constructor
            )

            self.pulse_toolbox.insertItem(
                i,
                pulse_form,
                f"{str(i)}: {pulse_specifier.get_printable_name()}"
            )

            # Select last item and set minimum heigt.
            self.pulse_toolbox.setCurrentWidget(pulse_form)
            pulse_form.parent().parent().setMinimumHeight(100)

    def remove_pulse_specifier(self, pulse_specifier, pb_constructor):
        """"Remove pulse specifier from Pb constructor."""
        pb_constructor.pulse_specifiers.remove(pulse_specifier)

        # Redraw toolbox
        self.update_pulse_list_toolbox()

        # Recompile pulseblock
        self.plot_current_pulseblock()

    def update_pulse_form_field(self, pulse_specifier, pulse_specifier_field, field_var):
        """ Update pulse specifier upon change of field, recompile and plot pb."""

        # Get value from changed field.
        if field_var == 'tref':
            value = pulse_specifier_field.currentText()
        else:
            value = pulse_specifier_field.text()

        # Update pulse specifier.
        if field_var == 'dur':
            pulse_specifier.dur = value
        elif field_var == 'offset':
            pulse_specifier.offset = value
        elif field_var == 'tref':
            pulse_specifier.tref = value
        else:
            pulse_specifier.pulsevar_dict[field_var] = value

        self.plot_current_pulseblock()

    def get_pulse_specifier_form(self, pulse_specifier, pb_constructor):

        """Change input fields if pulse selector dropdown has been changed."""

        # Setup QForm.
        form = QGroupBox()
        qform_layout = QFormLayout()
        form.setLayout(qform_layout)

        # Load pulsetype settings
        pulsetype_dict = self._get_pulsetype_dict_by_pb_type(pulse_specifier.pulsetype)

        input_widget_names = []

        for field in pulsetype_dict['fields']:

            # Add label.
            field_label = QLabel(field['label'])

            # Get field type
            field_input = self._get_pulse_fieldtype(field)

            # Add choices to combobox.
            if type(field_input) is QComboBox:
                    field_input.addItems(field['combo_choice'])

            # Auto create name of widget:
            input_widget_name = self._get_pulse_mod_field_name(
                field_dict = field,
                uid = pulse_specifier.uid
            )

            field_input.setObjectName(input_widget_name)

            # Define the function called upon change of fields.
            # Partial command needed to use lambda-type functions
            # in loop: https://stackoverflow.com/questions/11154227/pyqt-defining-signals-for-multiple-objects-in-loops
            pulse_mod_function = functools.partial(
                self.update_pulse_form_field,
                pulse_specifier,
                field_input,
                field['var']
            )

            # First look for the timing info:
            if field['var'] == 'dur':
                value = pulse_specifier.dur
            elif field['var'] == 'offset':
                value = pulse_specifier.offset
            elif field['var'] == 'tref':
                value = pulse_specifier.tref
            # If file does not contain timing info, look
            # at pulse parameter dictionary.
            else:
                value = pulse_specifier.pulsevar_dict[field['var']]

            qform_layout.addRow(field_label, field_input)

            # Update Combobox.
            if field['var'] == 'tref':
                field_input.setCurrentIndex(field_input.findText(value))
                field_input.currentIndexChanged.connect(pulse_mod_function)
            # Update QLineedit.
            else:
                field_input.setText(str(value))
                field_input.textEdited.connect(pulse_mod_function)

        delete_button = QPushButton("Delete Pulse")
        delete_button.setStyleSheet("background-color : #6a040f")

        remove_pulse_function = lambda: self.remove_pulse_specifier(
            pulse_specifier=pulse_specifier,
            pb_constructor=pb_constructor
        )

        delete_button.clicked.connect(remove_pulse_function)
        qform_layout.addRow("", delete_button)

        return form, qform_layout

    def setup_pulse_modification_form(self):
        """ Setup form displayed in every tab of "Defined-Pulse" Toolbox."""

        self.pulse_selector_form_static = QGroupBox()
        self.pulse_selector_form_static.setObjectName("pulse_static_toolbox")
        self.pulse_selector_channelselection = QLineEdit()
        self.pulse_selector_pulse_drop_down = QComboBox()

        # Set selector.
        self.set_pulsetype_combobox(self.pulse_selector_pulse_drop_down)

        # Connect to change function
        self.pulse_selector_pulse_drop_down.currentTextChanged.connect(self.build_pulse_input_fields)

        # Create one Form to contain the for fields that never change.
        self.pulse_selector_form_layout_static = QFormLayout()
        self.pulse_selector_form_layout_static.addRow(QLabel("Channel:"), self.pulse_selector_channelselection)
        self.pulse_selector_form_layout_static.addRow(QLabel("Pulse Type:"), self.pulse_selector_pulse_drop_down)
        self.pulse_selector_form_static.setLayout(self.pulse_selector_form_layout_static)


        # Add a second form containing the fields that change from pulsetype to pulsetype
        self.pulse_selector_form_variable = QGroupBox()
        self.pulse_selector_form_variable.setObjectName("pulse_var_toolbox")

        self.pulse_selector_form_layout_variable = QFormLayout()
        self.pulse_selector_form_variable.setLayout(self.pulse_selector_form_layout_variable)

        # Add forms to Hbox layout
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_static)
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_variable)

        # Build pulse-specific fileds.
        self.build_pulse_input_fields()

    def get_pb_contructor_list(self):
        """ Return list of names of all instanciated Pulseblock contructors."""
        return  [pb_constructor.name for pb_constructor in self.pulseblock_constructors]

    def get_pb_contructor_by_name(self, name):
        """ For a given pulseblock name, return the corresponding PulseblockConstrutor"""

        # Query associated pb constructor element.
        matching_constructors = [pb_constructor for pb_constructor in self.pulseblock_constructors if pb_constructor.name == name]

        if len(matching_constructors) > 1:
            pb_constructor = None
            self.log.warn(f"More than one Pulseblock contructors associated with curren pulseblock {name} found.")
        elif len(matching_constructors) == 0:
            self.log.warn('No matching pulseblock found.')
            pb_constructor = None
        else:
            pb_constructor = matching_constructors[0]

        return pb_constructor

    def get_current_pb_constructor(self):
        """ Return PulseblockCOnstructor of currently selected Pulseblock."""
        # Read current pulesblock name from Combobox.
        current_pb_name = self.widgets["pulseblock_combo"].currentText()

        return self.get_pb_contructor_by_name(current_pb_name)

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

        self.plot_current_pulseblock(update_variables=False)

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
        self.add_pb_popup.pulseblock_inherit_field.addItem("")
        self.add_pb_popup.pulseblock_inherit_field.addItems(self.get_pb_contructor_list())

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
        add_pb_button.clicked.connect(self.add_pulseblock_constructors_from_popup)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

        # Shot the pop-up
        self.add_pb_popup.show()

    def update_pulseblock_dropdown(self):
        """Update pulseblock dropdown"""

        self.widgets['pulseblock_combo'].clear()
        self.widgets['pulseblock_combo'].addItems(self.get_pb_contructor_list())

    def get_pulseblock_names(self):
        return self.pulseblocks.keys()


    def add_pulseblock_constructors_from_popup(self):
        """Create new pulseblock instance and add to pb dictionary"""

        # Get pulseblocks from Popup class
        pb_constructor = self.return_pulseblock_new_pulseblock_constructor()

        # Check if constructor with same name already exists
        if pb_constructor.name in [pb_constructor.name for pb_constructor in self.pulseblock_constructors]:
            self.showerror(f"You have already initilized a pulsblock with the name '{pb_constructor.name}'.")
            self.add_pb_popup.close()
            return

        # Add empty pulseblock constructor to pulseblock constructor list.
        self.pulseblock_constructors.append(
            pb_constructor
        )

         #Temporarliy disconnect the currentIndexChanged so it does not fire during the
        # constructor generation
        self.widgets["pulseblock_combo"].currentIndexChanged.disconnect()

        # Update pulseblock dropdown.
        self.update_pulseblock_dropdown()

        # Select newest pulseblock
        self.widgets["pulseblock_combo"].setCurrentText(pb_constructor.name)

        self.widgets["pulseblock_combo"].currentIndexChanged.connect(self.pulseblock_dropdown_changed)

        # Update toolbox.
        self.update_pulse_list_toolbox()

        # Close popup
        self.add_pb_popup.close()

    def gen_pulse_specifier(self, pulsetype_dict, pulse_data_dict):
        """ Generates instance of PulseSpecifier which contain full
        information of pulse (Pulsetype, channel_number, pulsetype, pulse_parameters,
        timing information)

        :pulsetype_dict: Dictionary specifying pulsetype (read from config JSON)
        :pulse_data_dict: Dictionary containing the pulse-specific cdata retreived from input fields.
        """

        pulse_specifier = PulseSpecifier(
            channel = pulse_data_dict["channel"],
            pulsetype = pulsetype_dict["pulseblock_type"],
            pulsetype_name = pulsetype_dict["name"]
        )

        # Add timing info.
        pulse_specifier.set_timing_info(
            offset=pulse_data_dict['offset'],
            dur=pulse_data_dict['dur'],
            tref=pulse_data_dict['tref']
        )

        # Add pulse var info.
        pulsevar_dict = {}

        for pulsedict_field in pulsetype_dict["fields"]:
            if not pulsedict_field['var'] in ['dur', 'tref', 'offset']:
                pulse_param_name = pulsedict_field['var']
                pulse_param_value = pulse_data_dict[pulse_param_name]
                pulsevar_dict[pulse_param_name] = pulse_param_value

        pulse_specifier.set_pulse_params(
            pulsevar_dict = pulsevar_dict
        )

        return pulse_specifier

    def add_pulse_from_form(self):
        """Get pulse info from form, create Pulse object and add to pulse list"""

        # Retrieve pulse:
        new_pulsetype = str(self.pulse_selector_pulse_drop_down.currentText())

        # Get pulsetype dict
        pulsetype_dict = self._current_pulsetype_dict()

        valid, puls_data_dict = self.read_pulse_params_from_form()

        if not valid:
            return

        # Generate dictionary fully specifying the pulse.
        pulse_specifier = self.gen_pulse_specifier(
            pulsetype_dict=pulsetype_dict,
            pulse_data_dict=puls_data_dict
        )

        # Add pulse to currently selected pulseblockconstructor.
        active_pb_constructor = self.get_current_pb_constructor()

        # Append pb_constructor to pulsebloack and attempt compilation.
        if active_pb_constructor is not None:
            active_pb_constructor.pulse_specifiers.append(pulse_specifier)
        else:
            self.showerror("Please create a Pulseblock before adding pulses.")
            return

        compilation_successful = self.compile_current_pulseblock()

        # If compilation failed, remove pb_specifiera and exit
        if not compilation_successful:
            active_pb_constructor.pulse_specifiers.remove(pulse_specifier)
            return

        # Update toolbox.
        self.update_pulse_list_toolbox()

        # Update completer
        self.update_var_completer()

        # Plot
        self.plot_current_pulseblock()


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
                # if typecasting failed, check value is variable or arithmetic expression.
                if key != "tref":
                    try:
                        # Try to resolve arithmetic expression containing variables.
                        simple_eval(val, names=self.vars)
                    except NameNotDefined:
                        typecast_error.append(key)
                        validated = False

        if not validated:
            if len(typecast_error) > 1:
                error_msg = f"Invalid entries for parameters: {typecast_error}"
            else:
                error_msg = f"Invalid entry for parameter {typecast_error[0]}"
            self.showerror(error_msg)

        return validated, pulsedict

    def read_pulse_params_from_form(self):
        """ Read pulse parameters from input form, perform
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
        error_dialog = QMessageBox.critical(
            self.gui, "Error",
            error_message,
            QMessageBox.Ok,
            QMessageBox.NoButton
        )

    def update_var_completer(self):
        """ Update variable completer """
        self.var_completer  = QCompleter(self.vars.keys())

        # Retrieve all Qlineedits
        var_completer_widgets = []

        # This groupbox contains the pulse
        for groubox in self.gui.findChildren(QGroupBox, "pulse_var_input"):
            for qlinedit in groubox.findChildren(QLineEdit):
                var_completer_widgets.append(qlinedit)

        # TODO: Find out why this doesn't work (issue148)
        # for qlinedit in self.widgets["pulse_scrollarea"].findChildren(QLineEdit):
        #     var_completer_widgets.append(qlinedit)
        #     self.log.info(qlinedit.objectName())

        for widget in var_completer_widgets:
                widget.setCompleter(self.var_completer)

    def setup_pulse_selector_form(self):
        self.pulse_selector_form_static = QGroupBox()
        self.pulse_selector_form_static.setObjectName("pulse_static_input")
        self.pulse_selector_channelselection = QLineEdit()
        self.pulse_selector_pulse_drop_down = QComboBox()

        # Set selector.
        self.set_pulsetype_combobox(self.pulse_selector_pulse_drop_down)

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

    def _get_pulsetype_dict_by_name_by_name(self, current_pulsetype):
        """ Return dictionary of pulsetype"""
        pulsetype_dict = [pulsedict for pulsedict in self.config_dict['pulse_types'] if pulsedict['name'] == current_pulsetype][0]
        return pulsetype_dict

    def _get_pulsetype_dict_by_pb_type(self, pb_type):
        """ Return dictionary of pulsetype by providing pulseblock type name."""
        pulsetype_dict = [pulsedict for pulsedict in self.config_dict['pulse_types'] if pulsedict['pulseblock_type'] == pb_type][0]
        return pulsetype_dict

    def _current_pulsetype_dict(self):
        """Get DIctionary of durrently selected pulsetype"""
        return self._get_pulsetype_dict_by_name_by_name(self._get_current_pulsetype())

    def _get_pulse_mod_field_name(self, field_dict, uid):
        """Create unique named for pulse info filed in the Toolbox

        :field_dict: The dictioanry containing the field info
        :uid: The uid of the parent PulseSpecifier object.
        """
        input_widget_name = f"{slugify(field_dict['label'])}_{str(uid)}"
        input_widget_name = f"{input_widget_name}_pulse_mod"

        return input_widget_name

    def _get_form_field_widget_name(self, field_dict):
        """Generates a unique name for pulse add form fields.

        :pulse_mod: If True, this function is called not from the Pulse
        Add form, but from the pulse modification form in th e
        Toolbox.
        """

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

            # Auto create name of widget:
            input_widget_name = self._get_form_field_widget_name(field)
            field_input.setObjectName(input_widget_name)

            self.pulse_selector_form_layout_variable.addRow(field_label, field_input)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()


    def set_pulsetype_combobox(self, combobox):
        for pulsetype in self.config_dict['pulse_types']:
            combobox.addItem(pulsetype['name'])


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

def launch(**kwargs):
    """ Launches the pulsemaster script """

    # logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    logger = kwargs['logger']

    # Instantiate Pulsemaster
    try:
        pulsemaster = PulseMaster(
            logger_client=logger, server_port=kwargs['server_port'], config=kwargs['config']
        )

        constructor = PulseblockConstructor(
            name='test',
            log=logger,
            var_dict = {}
        )
        pulsemaster.pulseblock_constructors.append(constructor)
        pulsemaster.update_pulseblock_dropdown()

    except KeyError:
        logger.error('Please make sure the module names for required servers and GUIS are correct.')
        time.sleep(15)
        raise

    pulsemaster.gui.app.exec_()
