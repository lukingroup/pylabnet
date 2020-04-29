from pylabnet.gui.pyqt.gui_handler import GUIHandler
import time


class StaticLineGUICheck():
    """TODO

    :gui_client: (object)
        GUI client to be called.
    :logger_client: (object)
        Logger client used for error logging in  @handle_gui_errors
        decorator.
    """

    def __init__(
        self,
        gui_client,
        staticline_daq,
        staticline_hdawg,
        logger_client
    ):

        # Instanciate gui handler
        self.gui_handler = GUIHandler(gui_client, logger_client)

        # store shutter client
        self.staticline_DAQ = staticline_daq
        self.staticline_HDAWG = staticline_hdawg

    def initialize_button(
        self,
        button_daq_widget='labelwave',
        button_daq_widget_label='wave_label',
        button_hdawg_widget='labeldisplay',
        button_hdawg_widget_label='display_label',
        button_daq_on_widget='wave_on_button',
        button_daq_on_widget_label='waveon',
        button_daq_off_widget='wave_off_button',
        button_daq_off_widget_label='waveoff',
        button_hdawg_on_widget='display_on_button',
        button_hdawg_on_widget_label='displayon',
        button_hdawg_off_widget='display_off_button',
        button_hdawg_off_widget_label='displayoff'
    ):
        """ Initialize label to shutter name, assigned label

        :button_label_widget: (string)
            Widget name of label of button toggling the shutter.
        :button_label_widget_label: (string)
            Name of label of button toggling the shutter.
        :button_widget: (string)
            Widget name of button.
        :button_widget_label: (string)
            Label of button widget.
        """

        # Assign LabelS
        label_widgets = [
            button_daq_widget,
            button_hdawg_widget
        ]

        label_labels = [
            button_daq_widget_label,
            button_hdawg_widget_label
        ]

        button_widgets = [
            button_daq_on_widget,
            button_daq_off_widget,
            button_hdawg_on_widget,
            button_hdawg_off_widget
        ]

        button_labels = [
            button_daq_on_widget_label,
            button_daq_off_widget_label,
            button_hdawg_on_widget_label,
            button_hdawg_off_widget_label
        ]

        for widget, label in zip(label_widgets, label_labels):
            self.gui_handler.assign_label(widget, label)

        # Assign buttons
        for widget, label in zip(button_widgets, button_labels):
            self.gui_handler.assign_event_button(widget, label)


        # Retrieve staticline names
        staticline_daq_name = self.staticline_DAQ.name
        staticline_hdawg_name = self.staticline_HDAWG.name


        # Set value of label staticline names.
        self.gui_handler.set_label(staticline_daq_name, button_daq_widget_label)
        self.gui_handler.set_label(staticline_hdawg_name, button_hdawg_widget_label)

    def check_buttons(self):
        """ Checks state of buttons and sets shutter accordingly"""
        if self.gui_handler.was_button_pressed(event_label=self.gui_handler.button_daq_on_widget_label):
            self.staticline_DAQ.up()
        elif self.gui_handler.was_button_pressed(event_label=self.gui_handler.button_daq_off_widget_label):
            self.staticline_DAQ.down()
        elif self.gui_handler.was_button_pressed(event_label=self.gui_handler.button_hdawg_on_widget_label):
            self.staticline_HDAWG.up()
        elif self.gui_handler.was_button_pressed(event_label=self.gui_handler.button_hdawg_off_widget_label):
            self.staticline_HDAWG.down()

    def run(self):

        # Initialize button
        self.initialize_button()

        # Mark running flag
        self.gui_handler.is_running = True
        while self.gui_handler.is_running:
            self.check_buttons()
            time.sleep(0.02)