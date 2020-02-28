from pylabnet.gui.pyqt.gui_handler import GUIHandler
import time


class ShutterControl():
    """Configures the shuttercontrol GUI enabling GUI control of a shutter.

    :gui_client: (object)
        GUI client to be called.
    :logger_client: (object)
        Logger client used for error logging in  @handle_gui_errors
        decorator.
    :shutter_client: (object)
        Client of shutter hardware class.
    """

    def __init__(self, gui_client, shutter_client, logger_client):

        # Instanciate gui handler
        self.gui_handler = GUIHandler(gui_client, logger_client)

        # Store labels
        self.shutter_button_open_label = None
        self.shutter_button_close_label = None

        # store shutter client
        self.shutter_client = shutter_client

    def initialize_button(self, button_label_widget='label_1', button_label_widget_label='shutterlabel',
                          button_open_widget='open_button', button_open_widget_label='shutterbutton_open',
                          button_close_widget='close_button', button_close_widget_label='shutterbutton_close'):
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

        # Assign Label
        self.gui_handler.assign_label(button_label_widget, button_label_widget_label)

        # Assign buttons
        self.gui_handler.assign_event_button(button_open_widget, button_open_widget_label)
        self.gui_handler.shutter_button_open_label = button_open_widget_label
        self.gui_handler.assign_event_button(button_close_widget, button_close_widget_label)
        self.gui_handler.shutter_button_close_label = button_close_widget_label

        # Retrieve shutter name from client.
        shutter_name = self.shutter_client.get_name()

        # Set value of label to shutter name.
        self.gui_handler.set_label(shutter_name, button_label_widget_label)

    def check_buttons(self):
        """ Checks state of buttons and sets shutter accordingly"""
        if self.gui_handler.was_button_pressed(event_label=self.gui_handler.shutter_button_open_label):
            self.shutter_client.open()
        elif self.gui_handler.was_button_pressed(event_label=self.gui_handler.shutter_button_close_label):
            self.shutter_client.close()

    def run(self):

        # Initialize button
        self.initialize_button()

        # Mark running flag
        self.gui_handler.is_running = True
        while self.gui_handler.is_running:
            self.check_buttons()
            time.sleep(0.02)
