import re
import copy
import numpy as np
import time
import pyqtgraph as pg
import json
import functools

from PyQt5.QtWidgets import QShortcut, QToolBox, QFileDialog, QMessageBox, QPushButton, QGroupBox, \
    QFormLayout, QComboBox, QWidget, QTableWidgetItem, QVBoxLayout, \
    QTableWidgetItem, QCompleter, QLabel, QLineEdit, QCheckBox, QGridLayout
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import QRect, Qt, QAbstractTableModel, QTimer, QVariant

from simpleeval import simple_eval, NameNotDefined

import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.hardware.awg.zi_hdawg import Driver
from pylabnet.utils.helper_methods import slugify
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import get_ip, unpack_launcher, load_config, load_script_config, get_gui_widgets, find_client
from pylabnet.utils.pulsed_experiments.pulsed_experiment import PulsedExperiment

from pylabnet.scripts.pulsemaster.pulseblock_constructor import PulseblockConstructor, PulseSpecifier
from pylabnet.scripts.pulsemaster.pulsemaster_customwidget import DictionaryTableModel, AddPulseblockPopup


class PulseMaster:

    # Generate all widget instances for the .ui to use
    # _plot_widgets, _legend_widgets, _number_widgets = generate_widgets()

    def __init__(self, config, ui='pulsemaster', logger_client=None, server_port=None, mw_source_client=None):
        """ TODO
        """

        self.log = logger_client

        # Load config dict.
        self.config_dict = load_script_config(
            script='pulsemaster',
            config=config,
            logger=self.log
        )

        # Initialize experiment config dict to be passed to PulsedExperiment
        self.exp_config_dict = dict()

        # Instanciate HD
        dev_id = self.config_dict['HDAWG_dev_id']
        self.hd = Driver(dev_id, logger=self.log)

        # Get microwave client
        self.mw_client = mw_source_client

        # Instantiate GUI window
        self.gui = Window(
            gui_template=ui,
            host=get_ip(),
            port=server_port
        )

        # Get Widgets
        self.widgets = get_gui_widgets(
            self.gui,
            ch_table=1,
            update_ch_button=1,
            add_pulse_layout=1,
            add_pulse_button=1,
            new_pulseblock_button=1,
            pulseblock_combo=1,
            variable_table_view=1,
            add_variable_button=1,
            pulse_list_vlayout=1,
            pulse_scrollarea=1,
            pulse_layout_widget=1,
            seq_var_table=1,
            load_seq_vars=1,
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
            load_pulseblock=1,
            preserve_bits=1
        )

        # Initialize empty pulseblock dictionary.
        self.pulseblocks = {}

        # Store filepath to sequence vars
        self.seq_var_filepath = None

        # Initialize empty dictionary containing the contruction
        # Instructions for the currently displayed pulseblock.
        self.pulseblock_constructors = []

        # Initialize Variable dict
        self.vars = {}

        self.variable_table = self.widgets['variable_table_view']

        self.variable_table_model = DictionaryTableModel(
            self.vars,
            header=["Variable", "Value"],
            editable=True
        )

        self.variable_table.setModel(self.variable_table_model)

        # Store completers
        self.var_completer = QCompleter(self.vars.keys())

        # Initialize Pulse Selector Form
        self.setup_pulse_selector_form()

        # Populate channel table
        self.populate_ch_table_from_dict()

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

        # Initialize timers for controlling when text boxes get updated
        self.timers = []

        # Initialize preserve_bits checkbox state in dictionary
        self.update_preserve_bits()

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

        # Assign all actions to buttons and data-change events
        self.assign_actions()

        # Apply all custom styles
        self.apply_custom_styles()

        # Set the number of plotting points for the pulse preview window
        if "plot_points" in self.config_dict:
            self.plot_points = self.config_dict["plot_points"]
        else:
            self.plot_points = 800 # Default value

        self.awg_running = False

    def apply_custom_styles(self):
        """Apply all style changes which are not specified in the .css file."""

        # Set background of custom PlotWidgets
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

        # Conect checkbox for DIO bit preservation option
        self.widgets["preserve_bits"].stateChanged.connect(self.update_preserve_bits)

        # Connect Add variable button.
        self.widgets['add_variable_button'].clicked.connect(self._add_row_to_var_table)

        # Connect "Update Channel Assignment" Button
        self.widgets['update_ch_button'].clicked.connect(self.populate_ch_table_from_dict)

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

    def update_preserve_bits(self):
        self.exp_config_dict["preserve_bits"] = self.widgets["preserve_bits"].isChecked()

    def get_pb_specifier_from_dict(self, pulsedict):
        """ Create PulseSpecifier object from dictionary."""

        pulsetype_dict = self._get_pulsetype_dict_by_pb_type(pulsedict['pulsetype'])

        pb_specifier = PulseSpecifier(
            channel=pulsedict['channel'],
            pulsetype=pulsedict['pulsetype'],
            pulsetype_name=pulsedict['name'],
            is_analog=simple_eval(pulsetype_dict["is_analog"])
        )

        pb_specifier.set_timing_info(
            offset=pulsedict['offset'],
            dur=pulsedict['dur'],
            tref=pulsedict['tref']
        )

        pb_specifier.set_pulse_params(
            pulsevar_dict=pulsedict['pulse_vars']
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
                var_dict=new_var_dict,
                config=self.config_dict
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
        pb_dict, _ = self.load_json_dict()

        # Create pulseblock contructor.
        imported_contructor = self.get_pb_constructor_from_dict(pb_dict)

        # Check if pulseblock with same name alraedy exists
        if imported_contructor.name in [constructor.name for constructor in self.pulseblock_constructors]:
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

        # Update sequence var dict
        self.get_seq_var_dict_from_previous()

        # Get sequence template from textbox.
        seq_template = self.widgets['seqt_textedit'].toPlainText()
        if seq_template == "":
            self.showerror('No sequence template defined.')
            return

        # Find placeholders for pulseblocks in the template
        # Define regex: anything enclosed between the marker strings, the string
        # in the middle cannot include the marker itself
        marker = "$"
        regex = f'\{marker}([^{marker}]+)\{marker}'
        found_placeholders = [match.group(1) for match in re.finditer(regex, seq_template)]

        # Remove duplicates since they will be replaced together in one step
        found_placeholders = set(found_placeholders)

        # Compile and get the pulseblock for each pulseblock that appears in the
        # sequence template string
        required_pulseblocks = []
        for name in found_placeholders:
            pb_constructor = self.get_pb_contructor_by_name(name)
            if pb_constructor is None:
                continue
            self.compile_pulseblock(pb_constructor)
            required_pulseblocks.append(pb_constructor.pulseblock)

        # Retrieve AWG number from settings.
        awg_num = self.widgets['awg_num_val'].value()

        # Retrieve placeholder dictionary from table.
        placeholder_dict = self.get_seq_var_dict()

        self.pulsed_experiment = PulsedExperiment(
            pulseblocks=required_pulseblocks,
            assignment_dict=self.ch_assignment_dict,
            hd=self.hd,
            mw_client=self.mw_client,
            placeholder_dict=placeholder_dict,
            exp_config_dict=self.exp_config_dict,
            use_template=False,
            sequence_string=seq_template,
            marker_string=marker,
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
        name = QFileDialog.getSaveFileName(self.gui, 'Save File', '', filetype)
        with open(name[0], "w") as text_file:
            text_file.write(data)

    def json_file_save(self, data):
        """ Generic file saving."""
        name = QFileDialog.getSaveFileName(self.gui, 'Save File', '', "JSON files (*.json)")
        with open(name[0], 'w') as fp:
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

    def set_seq_var_dict(self, seq_var_dict):
        """ Initialize Sequencer Variable table. """

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

    def get_seq_var_dict_from_file(self):
        """ Load assignment dictionary from file."""

        # Get filepath from file-sepector popup.
        seq_var_dict, filename = self.load_json_dict()
        self.seq_var_filepath = filename
        self.set_seq_var_dict(seq_var_dict)

    def get_seq_var_dict_from_previous(self):
        """ Read at stored sequence variable dict filepaths and loads it"""
        if self.seq_var_filepath is not None:
            f = open(self.seq_var_filepath)
            seq_var_dict = json.load(f)
            self.set_seq_var_dict(seq_var_dict)

    def get_filename(self, filetype="JSON files (*.json)"):
        """Open file selector widget and get files."""
        return QFileDialog.getOpenFileName(self.gui, 'Open file', '', filetype)

    def load_json_dict(self):
        """Open pop-up, search for JSON file and return as dict."""

        filename = self.get_filename()

        f = open(filename[0])

        # returns JSON object as
        # a dictionary
        dictionary = json.load(f)

        return dictionary, filename[0]

    def prep_plotdata(self, pb_obj):

        self.widgets["pulse_layout_widget"].clear()

        # Iterate through p_dict.keys() and dflt_dict.keys()
        # and create a trace for each channel
        #  - create sorted list of channels

        d_ch_set = set(pb_obj.dflt_dict.keys())
        p_ch_set = set(pb_obj.p_dict.keys())
        ch_list = list(d_ch_set | p_ch_set)
        ch_list.sort()

        # - iterate through ch_list
        for ch_index, ch in enumerate(ch_list):

            ## Build x_ar, y_ar, text_ar

            ## Analog channel
            if ch.is_analog:
                pulse_items = pb_obj.p_dict[ch]
                default_item = pb_obj.dflt_dict[ch]

                x_ar = []
                y_ar = []

                # Create a fictional "zeroth pulse" to end at t=0 so that we
                # draw the default pulse value from 0 until the start of the
                # first pulse.
                t2 = 0

                for p_item in pulse_items:

                    # Edges of the current pulse
                    new_t1 = p_item.t0
                    new_t2 = p_item.t0 + p_item.dur

                    # Draw the default function from the previous to current pulse
                    # Low density spacing since it's usually a constant
                    t_ar = np.linspace(t2, new_t1, 10)
                    x_ar.extend(t_ar)
                    y_ar.extend(default_item.get_value(t_ar))

                    t1, t2 = new_t1, new_t2

                    # Draw the current pulse at high grid density
                    t_ar = np.linspace(t1, t2, self.plot_points)
                    x_ar.extend(t_ar)
                    y_ar.extend(p_item.get_value(t_ar))

                # Put zero-point after the last pulse
                x_ar.append(new_t2)
                y_ar.append(0)

                # Put zero-point at the end of pulseblock (different from previous
                # since the channel could end before other channels)
                x_ar.append(pb_obj.dur)
                y_ar.append(0)

                # Normalize the wave height and offset by channel index
                y_ar /= (2.5 * np.max(y_ar))
                y_ar += (ch_index + 0.4)

            ## Digital channel
            else:
                # initial zero-point - default pulse object printout
                x_ar = [0]
                y_ar = [ch_index]

                if ch in pb_obj.dflt_dict.keys():
                    text_ar = [str(pb_obj.dflt_dict[ch])]
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
                                    f'{t1:.2e}',
                                    str(p_item),
                                    f'{t2:.2e}', f'{t2:.2e}'
                                ]
                            )
                        else:
                            text_ar.extend(
                                [
                                    f'{t1:.2e}', f'{t1:.2e}',
                                    str(p_item),
                                    f'{t2:.2e}', f'{t2:.2e}'
                                ]
                            )

                # final zero-point
                x_ar.append(pb_obj.dur)
                y_ar.append(ch_index)
                text_ar.append(f'{pb_obj.dur:.2e}')

            pen = pg.mkPen(
                color=self.gui.COLOR_LIST[
                    ch_index
                ],
                width=3
            )
            self.widgets["pulse_layout_widget"].addLegend()
            self.widgets["pulse_layout_widget"].plot(x_ar, y_ar, pen=pen, name=ch.name)

    def compile_pulseblock(self, pulseblock_constructor, update_variables=True):
        """ Compile a specified pulseblock

        :update_variables: If True, update variables.
        """

        # Do nothing if no constructor found.
        if pulseblock_constructor == None:
            return

        # Update variables.
        if update_variables:
            self._update_variable_dict()

        # Update variable dict
        pulseblock_constructor.var_dict = self.vars

        # Try to compile the pulseblock
        try:
            pulseblock_constructor.compile_pulseblock()
            compilation_successful = True
            self.log.info(f"Successfully compiled pulseblock {pulseblock_constructor.name}.")
        except ValueError as e:
            self.showerror(str(e))
            compilation_successful = False

        return compilation_successful

    def compile_current_pulseblock(self, update_variables=True):
        """Compile the current pulseblock

        :update_variables: If True, update variables.
        """

        # Retrieve current pulseblock contructor and compile it
        pb_constructor = self.get_current_pb_constructor()
        compilation_successful = self.compile_pulseblock(pb_constructor, update_variables)

        return compilation_successful

    def plot_current_pulseblock(self, update_variables=True):

        # Compile pulseblock
        if not self.compile_current_pulseblock(update_variables):
            return

        self.prep_plotdata(self.get_current_pb_constructor().pulseblock)

    def copy_pulseblock_constructor(self, pb_constructor, new_name):
        """ Generate new instance of pulseblock constructor which is identical to reference instance,
        with the excpetion of the name.

        :pb_constructor: PulseblockConstructor object to be copied.
        :new_name: New name of copied instance.
        """

        # Retrieve pulseblock contructor dictionary from old constructor.
        pb_constructor_dict = pb_constructor.get_dict()

        # Generate copy of constructor using the dictionary.
        copied_constructor = self.get_pb_constructor_from_dict(pb_constructor_dict)

        # Replace name of copy.
        copied_constructor.name = new_name

        return copied_constructor

    def return_pulseblock_new_pulseblock_constructor(self):
        """ Add new pulseblock by clicking the "Add Pb" button."""

        inherit_combobox_text = self.add_pb_popup.pulseblock_inherit_field.currentText()
        pb_name = self.add_pb_popup.pulseblock_name_field.text()

        # If no option is choosen in the dropdown, generate new pb contructor.
        if inherit_combobox_text == "":
            pb_constructor = PulseblockConstructor(
                name=pb_name,
                log=self.log,
                var_dict=self.vars,
                config=self.config_dict
            )

        # Otherwise copy and rename constructor.
        else:
            ref_pb_constructor = self.get_pb_contructor_by_name(inherit_combobox_text)
            pb_constructor = self.copy_pulseblock_constructor(
                pb_constructor=ref_pb_constructor,
                new_name=pb_name
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
                pb_constructor=current_pb_constructor,
                pulse_index=i
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

    def shift_pulse_specifier(self, pulse_specifier, pb_constructor, direction):
        """ Move a pulse specifier by a certain number of slots forward/backward
            in a PB constructor.
        """

        index = pb_constructor.pulse_specifiers.index(pulse_specifier)
        new_index = index + direction

        if new_index < 0 or new_index >= len(pb_constructor.pulse_specifiers):
            self.showerror(f"Moving pulse type {pulse_specifier.pulsetype_name}"
                           f"by {direction} would move it out of bounds.")
            return

        # Create a copy of the original
        pulse_specifiers_orig = copy.copy(pb_constructor.pulse_specifiers)

        # Shift pulse_spec position
        pb_constructor.pulse_specifiers.remove(pulse_specifier)
        pb_constructor.pulse_specifiers.insert(new_index, pulse_specifier)

        # Revert back to original order if compile failed
        if not self.compile_pulseblock(pb_constructor):
            pb_constructor.pulse_specifiers = pulse_specifiers_orig

        # Redraw toolbox
        self.update_pulse_list_toolbox()
        # Recompile pulseblock
        self.plot_current_pulseblock()

    def update_pulse_form_field(self, pulse_specifier, pulse_specifier_field, field_var, widgets_dict, pulse_index):
        """ Update pulse specifier upon change of field, recompile and plot pb."""

        # Load pulsetype settings
        pulsetype_dict = self._get_pulsetype_dict_by_pb_type(pulse_specifier.pulsetype)

        # Get value from changed field.
        if field_var == 'tref':
            value = pulse_specifier_field.currentText()
        elif type(pulse_specifier_field) is QLineEdit:
            value = pulse_specifier_field.text()
        elif type(pulse_specifier_field) is QCheckBox:
            value = pulse_specifier_field.isChecked()

        # Update pulse specifier.
        if field_var == 'dur':
            pulse_specifier.dur = value
        elif field_var == 'offset':
            pulse_specifier.offset = value
        elif field_var == 'tref':
            pulse_specifier.tref = value
        elif field_var == 'ch':
            # Check channel type matches
            channel_is_analog = (self.ch_assignment_dict[value][0] == "analog")
            if channel_is_analog != eval(pulsetype_dict["is_analog"]):
                self.showerror(f"Type of pulse {pulsetype_dict['name']} "
                               f"does not match channel {value}.")
                return
            pulse_specifier.channel = value

        # If we are modifying IQ to be on but mod is not on, then give an error
        elif field_var == 'iq' and value and not pulse_specifier.pulsevar_dict["mod"]:
            pulse_specifier_field.setChecked(False)
            self.showerror("IQ must be done with modulation on!")
            return
        # If we are turning off mod but IQ is on, then give an error
        elif field_var == 'mod' and not value and pulse_specifier.pulsevar_dict["iq"]:
            pulse_specifier_field.setChecked(True)
            self.showerror("IQ must be done with modulation on!")
            return
        # Update variables in the pulsevar_dict
        else:
            pulse_specifier.pulsevar_dict[field_var] = value

        # Handle changes to the form that need to take place when we var box is
        # checked/unchecked.
        if field_var.endswith("_var"):

            # Get the field of the parent var that the checkbox refers to
            var_parent_field = widgets_dict[field_var[:-4]]
            var_placeholder_name = f"{field_var}_{self.widgets['pulseblock_combo'].currentText()}_{pulse_index}"

            if value:
                var_parent_field.setEnabled(False)
                var_parent_field.setText(var_placeholder_name)
            else:
                var_parent_field.setEnabled(True)
                var_parent_field.setText("")

            # If the t0 term is variable, we must set to "At End of Sequence",
            # otherwise we have no idea when the pulse happens.
            if field_var == "offset_var":
                tref_field = widgets_dict["tref"]
                tref_field.setCurrentIndex(tref_field.findText("At End of Sequence"))
                self.update_pulse_form_field(pulse_specifier, tref_field, "tref", widgets_dict, pulse_index)

            # Store the updated value in parent
            self.update_pulse_form_field(pulse_specifier, var_parent_field, field_var[:-4], widgets_dict, pulse_index)

        self.plot_current_pulseblock()

    def get_pulse_specifier_form(self, pulse_specifier, pb_constructor, pulse_index):
        """Change input fields if pulse selector dropdown has been changed."""

        # Setup widget box
        widget_box = QGroupBox()
        widget_layout = QGridLayout()
        widget_box.setLayout(widget_layout)

        # Load pulsetype settings
        pulsetype_dict = self._get_pulsetype_dict_by_pb_type(pulse_specifier.pulsetype)

        widgets_dict = {}

        # Add channel as an extra field since it is not in the pulse fields
        pulse_fields = [{'label': 'Channel', 'input_type': 'QLineEdit', 'var': 'ch'}] \
            + pulsetype_dict['fields']

        # Add the labels and fields for each variable
        for row, field in enumerate(pulse_fields):

            # Add label.
            field_label = QLabel(field['label'])

            # Get field type
            field_input = self._get_pulse_fieldtype(field)
            widgets_dict[field['var']] = field_input

            # Add choices to combobox.
            if type(field_input) is QComboBox:
                field_input.addItems(field['combo_choice'])

            # Auto create name of widget:
            input_widget_name = self._get_pulse_mod_field_name(
                field_dict=field,
                uid=pulse_specifier.uid
            )

            field_input.setObjectName(input_widget_name)

            # Define the function called upon change of fields.
            # Partial command needed to use lambda-type functions
            # in loop: https://stackoverflow.com/questions/11154227/pyqt-defining-signals-for-multiple-objects-in-loops
            pulse_mod_function = functools.partial(
                self.update_pulse_form_field,
                pulse_specifier,
                field_input,
                field['var'],
                widgets_dict,
                pulse_index
            )

            # First look for the timing info:
            if field['var'] == 'dur':
                value = pulse_specifier.dur
            elif field['var'] == 'offset':
                value = pulse_specifier.offset
            elif field['var'] == 'tref':
                value = pulse_specifier.tref
            # Next look at the channel info
            elif field['var'] == 'ch':
                value = pulse_specifier.channel
            # If file does not contain timing info, look
            # at pulse parameter dictionary.
            else:
                value = pulse_specifier.pulsevar_dict[field['var']]

            # Column is 0 (first column) unless it is specified.
            # Column 0 fields occupy 3 columns, other column fields occupy 1.
            # Multiply col number by 4 to account for space taken by the
            # previous col (1 for label, 3 for field).
            # Widgets with column != 0 occupy the previous row.
            if 'col' in field:
                wid_col = 4 * field['col']
                wid_row = row - 1
                col_width = 1
            else:
                wid_col = 0
                wid_row = row
                col_width = 3

            widget_layout.addWidget(field_label, wid_row, wid_col, 1, 1) # Label
            widget_layout.addWidget(field_input, wid_row, wid_col + 1, 1, col_width) # Field

            # Update the value of the fields being displayed, and connect them
            # to the correct update function.
            if field['var'] == 'tref':
                field_input.setCurrentIndex(field_input.findText(value))
                field_input.currentIndexChanged.connect(pulse_mod_function)

            elif type(field_input) is QLineEdit:
                field_input.setText(str(value))

                # Create a timer to prevent the pulse update function from being called immediately
                self.timers.append(QTimer())
                self.timers[-1].setSingleShot(True)
                self.timers[-1].setInterval(300)
                self.timers[-1].timeout.connect(pulse_mod_function)
                field_input.textEdited.connect(self.timers[-1].start)

            elif type(field_input) is QCheckBox:
                field_input.setChecked(bool(value))
                field_input.clicked.connect(pulse_mod_function)

        # Add buttons to move pulse up/down
        def pulse_up_function(): return self.shift_pulse_specifier(
            pulse_specifier, pb_constructor, -1)

        def pulse_down_function(): return self.shift_pulse_specifier(
            pulse_specifier, pb_constructor, +1)

        up_button = QPushButton("Move Up")
        up_button.setStyleSheet("background-color : #fc766aff")
        up_button.clicked.connect(pulse_up_function)
        widget_layout.addWidget(up_button, row + 1, 0, 1, 3)

        down_button = QPushButton("Move Down")
        down_button.setStyleSheet("background-color : #5b84b1ff")
        down_button.clicked.connect(pulse_down_function)
        widget_layout.addWidget(down_button, row + 1, 3, 1, 3)

        row += 1 # Move the row index to the next row

        # Add delete button
        delete_button = QPushButton("Delete Pulse")
        delete_button.setStyleSheet("background-color : #6a040f")

        def remove_pulse_function(): return self.remove_pulse_specifier(
            pulse_specifier=pulse_specifier,
            pb_constructor=pb_constructor
        )

        delete_button.clicked.connect(remove_pulse_function)
        widget_layout.addWidget(delete_button, row + 1, 0, 1, 6)

        return widget_box, widget_layout

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

        self.pulse_selector_form_layout_variable = QGridLayout()
        self.pulse_selector_form_variable.setLayout(self.pulse_selector_form_layout_variable)

        # Add forms to Hbox layout
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_static)
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_variable)

        # Build pulse-specific fileds.
        self.build_pulse_input_fields()

    def get_pb_contructor_list(self):
        """ Return list of names of all instanciated Pulseblock contructors."""
        return [pb_constructor.name for pb_constructor in self.pulseblock_constructors]

    def get_pb_contructor_by_name(self, name):
        """ For a given pulseblock name, return the corresponding PulseblockConstrutor"""

        # Query associated pb constructor element.
        matching_constructors = [pb_constructor for pb_constructor in self.pulseblock_constructors if pb_constructor.name == name]

        if len(matching_constructors) > 1:
            pb_constructor = None
            self.log.warn(f"More than one Pulseblock contructors associated with curren pulseblock {name} found.")
        elif len(matching_constructors) == 0:
            self.log.warn(f'No pulseblock matching name {name} found.')
            pb_constructor = None
        else:
            pb_constructor = matching_constructors[0]

        return pb_constructor

    def get_current_pb_constructor(self):
        """ Return PulseblockConstructor of currently selected Pulseblock."""
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
                continue

            # Try typecast
            try:
                # Typecast and update data.
                var_val_float = float(var_val)
            except ValueError:
                self.log.warn(f'Variable value {var_val} cannot be typecast to float.')
                validated = False

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
            self.showerror(f"You have already initilized a pulseblock with the name '{pb_constructor.name}'.")
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

        # Update the plotting window (clears it)
        self.plot_current_pulseblock()

    def gen_pulse_specifier(self, pulsetype_dict, pulse_data_dict):
        """ Generates instance of PulseSpecifier which contain full
        information of pulse (Pulsetype, channel_number, pulsetype, pulse_parameters,
        timing information)

        :pulsetype_dict: Dictionary specifying pulsetype (read from config JSON
        :pulse_data_dict: Dictionary containing the pulse-specific cdata retreived from input fields.
        """

        pulse_specifier = PulseSpecifier(
            channel=pulse_data_dict["channel"],
            pulsetype=pulsetype_dict["pulseblock_type"],
            pulsetype_name=pulsetype_dict["name"],
            is_analog=simple_eval(pulsetype_dict["is_analog"])
        )

        # Add timing info.
        pulse_specifier.set_timing_info(
            offset=pulse_data_dict['offset'],
            dur=pulse_data_dict['dur'],
            tref=pulse_data_dict['tref']
        )

        # Add pulse var info.
        pulsevar_dict = {}

        # For each field specified in JSON, extract data from input fields
        # Skip over the timing fields that were handled earlier
        for pulsedict_field in pulsetype_dict["fields"]:
            if not pulsedict_field['var'] in ['dur', 'tref', 'offset']:
                pulse_param_name = pulsedict_field['var']
                pulse_param_value = pulse_data_dict[pulse_param_name]
                pulsevar_dict[pulse_param_name] = pulse_param_value

        pulse_specifier.set_pulse_params(
            pulsevar_dict=pulsevar_dict
        )

        return pulse_specifier

    def add_pulse_from_form(self):
        """Get pulse info from form, create Pulse object and add to pulse list"""

        # Retrieve pulse:
        new_pulsetype = str(self.pulse_selector_pulse_drop_down.currentText())

        # Get pulsetype dict
        pulsetype_dict = self._current_pulsetype_dict()

        valid, pulse_data_dict = self.read_pulse_params_from_form()

        if not valid:
            return

        # Generate dictionary fully specifying the pulse.
        pulse_specifier = self.gen_pulse_specifier(
            pulsetype_dict=pulsetype_dict,
            pulse_data_dict=pulse_data_dict
        )

        # Add pulse to currently selected pulseblockconstructor.
        active_pb_constructor = self.get_current_pb_constructor()

        # Append pb_constructor to pulseblock and attempt compilation.
        if active_pb_constructor is not None:

            active_pb_constructor.pulse_specifiers.append(pulse_specifier)
        else:
            self.showerror("Please create a Pulseblock before adding pulses.")
            return

        compilation_successful = self.compile_current_pulseblock()

        # If compilation failed, remove pb_specifiers and exit
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

        # Keys = String from config specifying the field type
        # Values = (QObject for the field, Function to extract the field's value)
        input_field_handlers = {
            "QLineEdit": (QLineEdit, lambda obj: obj.text()),
            "QComboBox": (QComboBox, lambda obj: obj.currentText()),
            "QCheckBox": (QCheckBox, lambda obj: obj.isChecked())
        }

        # Get the name and field type from config file
        field_names = [(self._get_form_field_widget_name(field), field['input_type']) for field in pulsetype_dict['fields'] if field['input_type'] in input_field_handlers]

        # Get the variable name that this field should be stored as
        field_vars = [field['var'] for field in pulsetype_dict['fields'] if field['input_type'] in input_field_handlers]
        field_values = []

        # Create the specified QObject and apply the function to get the relevant
        # data in the pulse input fields.
        for (field_name, field_type) in field_names:
            field_type_obj, field_type_fn = input_field_handlers[field_type]

            field_value = self.pulse_selector_form_variable.findChild(field_type_obj, field_name)
            field_value = field_type_fn(field_value)

            field_values.append(field_value)

        pulsedict_data = dict(zip(field_vars, field_values))
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

        # Get data from fields
        pulsetype_dict = self._current_pulsetype_dict()
        pulsedict_data = self.return_pulsedict(pulsetype_dict)

        # Validate data
        data_validated, pulsedict = self.clean_and_validate_pulsedict(pulsedict_data)
        if not data_validated:
            return False, None

        # IQ setting must be ticked with Modulation setting
        if ("iq" in pulsedict and pulsedict["iq"] and
                "mod" in pulsedict and not pulsedict["mod"]):
            self.showerror("IQ setting cannot be set without modulation!")
            return False, None

        channel = self.pulse_selector_channelselection.text()

        # Create a list of channel names that this pulse uses
        # Would be a 1-element list for a normal pulse and 2-element for IQ pulse
        if "iq" in pulsedict and pulsedict["iq"]:
            pulse_ch_list = [channel + "_i", channel + "_q"]
        else:
            pulse_ch_list = [channel]

        # Check if all channels that are required are specified
        if not all(name in self.ch_assignment_dict.keys() for name in pulse_ch_list):
            self.showerror("Please provide valid channel name.")
            return False, None

        # Check that the specified channels for IQ are not in the same core
        # if len(pulse_ch_list) > 1:
        #     # Subtract 1 to make 0-indexed
        #     ch_num_list = [(self.ch_assignment_dict[ch][1] - 1) for ch in pulse_ch_list]

            # Divide by 2 to see if same core (e.g. channels 0, 1 // 2 = 0)
            # ch_num_list = [ch//2 for ch in ch_num_list]
            # if len(ch_num_list) != len(set(ch_num_list)):
            #     self.showerror("Channels for the IQ mixing must be in different cores.")
            #     return False, None

        # Add channel to dict
        pulsedict['channel'] = channel

        # Check that the pulse type matches the channel type
        for ch in pulse_ch_list:
            channel_is_analog = (self.ch_assignment_dict[ch][0] == "analog")
            if channel_is_analog != eval(pulsetype_dict["is_analog"]):
                self.showerror(f"Type of pulse {pulsetype_dict['name']} "
                               f"does not match channel {ch}.")
                return False, None

        return True, pulsedict

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
        self.var_completer = QCompleter(self.vars.keys())

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

        self.pulse_selector_form_layout_variable = QGridLayout()
        self.pulse_selector_form_variable.setLayout(self.pulse_selector_form_layout_variable)

        # Add forms to Hbox layout
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_static)
        self.widgets['add_pulse_layout'].addWidget(self.pulse_selector_form_variable)

        # Build pulse-specific fileds.
        self.build_pulse_input_fields()

    def _remove_variable_pulse_fields(self):
        """Remove all pulse-type specific fields from layout."""
        for i in reversed(range(self.pulse_selector_form_layout_variable.count())):
            self.pulse_selector_form_layout_variable.itemAt(i).widget().setParent(None)

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
        """Get Dictionary of durrently selected pulsetype"""
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
        """Determine input field type."""
        # Build field.
        field_type = field_dict['input_type']
        if field_type == 'QLineEdit':
            field_input = QLineEdit()
        elif field_type == 'QComboBox':
            field_input = QComboBox()
        elif field_type == 'QCheckBox':
            field_input = QCheckBox()
        else:
            self.log.warn(f"Unknown field type {field_type} found.")
            return

        return field_input

    def build_pulse_input_fields(self):
        """Change input fields if pulse selector dropdown has been changed."""

        # Remove old entries.
        self._remove_variable_pulse_fields()

        # Load pulsetype settings
        pulsetype_dict = self._current_pulsetype_dict()

        widgets_dict = {}

        for row, field in enumerate(pulsetype_dict['fields']):
            # Create widget object from field type
            field_input = self._get_pulse_fieldtype(field)
            widgets_dict[field['var']] = field_input

            # Add label.
            field_label = QLabel(field['label'])

            # Add choices to combobox.
            if type(field_input) is QComboBox:
                field_input.addItems(field['combo_choice'])

            # Auto create name of widget:
            input_widget_name = self._get_form_field_widget_name(field)
            field_input.setObjectName(input_widget_name)

            # Column is 0 (first column) unless specified. x 2 to account for space
            # taken by the label. Widgets with column != 0 occupy the previous row.
            if 'col' in field:
                wid_col = 2 * field['col']
                wid_row = row - 1
            else:
                wid_col = 0
                wid_row = row

            self.pulse_selector_form_layout_variable.addWidget(field_label, wid_row, wid_col)
            self.pulse_selector_form_layout_variable.addWidget(field_input, wid_row, wid_col + 1)

            # Disable var checkboxes; this will only be allowed in the pulse
            # selector dropdown.
            if field['var'].endswith("_var"):
                field_input.setEnabled(False)

        # Make the sinuoidal checkbox affect whether the freq/phase boxes are
        # enabled.
        if "mod" in widgets_dict:
            mod_widget = widgets_dict["mod"]
            freq_widget = widgets_dict["mod_freq"]
            phase_widget = widgets_dict["mod_ph"]

            # Start out disabled with text 0
            freq_widget.setEnabled(False)
            freq_widget.setText("0")
            phase_widget.setEnabled(False)
            phase_widget.setText("0")

            # For subsequent times, the text fields are editable or not depending
            # on the state of the modulation checkbox.
            def modulation_fields_editable():
                freq_widget.setEnabled(mod_widget.isChecked())
                phase_widget.setEnabled(mod_widget.isChecked())

            mod_widget.stateChanged.connect(modulation_fields_editable)

        # Apply CSS stylesheet
        self.gui.apply_stylesheet()

    def set_pulsetype_combobox(self, combobox):
        for pulsetype in self.config_dict['pulse_types']:
            combobox.addItem(pulsetype['name'])

    def set_channel_completer(self):
        """Reset the autocomplete for the channel selection."""
        completer = QCompleter(self.ch_assignment_dict.keys())
        self.pulse_selector_channelselection.setCompleter(completer)

    def load_ch_assignment_from_dict(self):
        """Read in channel assignment dictionary and store as member variable."""
        # Load channel assignment.
        ch_assignment_dict = load_config(
            config_filename=self.config_dict['ch_dict'],
            logger=self.log
        )

        # Check for duplciate channels
        channels = []
        for item in ch_assignment_dict.values():
            if item not in channels:
                channels.append(item)
            else:
                self.showerror(f"Channel number {item} is duplicated in the "
                               "chanel assignment dictionary. ")
                return

        self.ch_assignment_dict = ch_assignment_dict

    def populate_ch_table_from_dict(self):
        '''Populate channel assignment table from channel assignment dict.'''

        # Update channel assignments from dict
        self.load_ch_assignment_from_dict()

        self.model = DictionaryTableModel(self.ch_assignment_dict, header=["Channel Name", "Type", "DIO Bit / Channel"])
        self.widgets['ch_table'].setModel(self.model)

        # Update completer.
        self.set_channel_completer()

        self.log.info('Channel settings successfully loaded.')


def launch(**kwargs):
    """ Launches the pulsemaster script """

    # logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    logger = kwargs['logger']

    try:
        mw_source_client = find_client(
            clients=kwargs['clients'],
            settings=kwargs['config'],
            client_type='HMC_T2220',
            logger=logger)
    except:
        mw_source_client = None

    # Instantiate Pulsemaster
    try:
        pulsemaster = PulseMaster(
            logger_client=logger, server_port=kwargs['server_port'],
            config=kwargs['config'], mw_source_client=mw_source_client
        )

        constructor = PulseblockConstructor(
            name='test',
            log=logger,
            var_dict={},
            config=pulsemaster.config_dict
        )
        pulsemaster.pulseblock_constructors.append(constructor)
        pulsemaster.update_pulseblock_dropdown()

    except KeyError:
        logger.error('Please make sure the module names for required servers and GUIS are correct.')
        time.sleep(15)
        raise

    pulsemaster.gui.app.exec_()
