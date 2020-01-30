from pylabnet.gui.pyqt.gui_handlers.gui_handler import GUIHandler
from pylabnet.utils.decorators.gui_decorators import gui_connect_check
import time

class ShutterGUIHandler(GUIHandler):

    def __init__(self, client=None):
        """
        Instantiates shutter gui

        :param shutter_client: (obj)
            instance of shutter client
        """

        # Instanciate parent class.
        super(ShutterGUIHandler, self).__init__(client)

        # Store labels
        self.shutter_button_open_label = None
        self.shutter_button_close_label = None

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
        self.assign_label(button_label_widget, button_label_widget_label)

        # Assign buttons
        self.assign_event_button(button_open_widget, button_open_widget_label)
        self.shutter_button_open_label = button_open_widget_label
        self.assign_event_button(button_close_widget, button_close_widget_label)
        self.shutter_button_close_label = button_close_widget_label

        # Retrieve shutter name from client.
        shutter_name = self.client.get_name()

        # Set value of label to shutter name.
        self.set_label(shutter_name, button_label_widget_label)

    def check_buttons(self):
        """ Checks state of buttons and sets shutter accordingly"""
        if self.was_button_pressed(event_label=self.shutter_button_open_label):
            self.client.open()
            #self.gui.change_button_background_color(self.shutter_button_open_label, 'red')
        elif self.was_button_pressed(event_label=self.shutter_button_close_label):
            self.client.close()

    def run(self):

        # Mark running flag
        self.is_running = True
        while self.is_running:
            self.check_buttons()
            time.sleep(0.02)
