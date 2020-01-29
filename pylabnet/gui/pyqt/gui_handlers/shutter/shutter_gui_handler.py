from pylabnet.gui.pyqt.gui_handlers.gui_handler import GUIHandler
from pylabnet.utils.decorators.gui_decorators import gui_connect_check

class ShutterGUIHandler(GUIHandler):

    def __init__(self, client=None):
        """
        Instantiates shutter gui

        :param shutter_client: (obj)
            instance of shutter client
        """

        # Instanciate parent class.
        super(ShutterGUIHandler, self).__init__(client)

        self.button_widget_label = None
        self.button_widget_label = None

    def initialize_button(self, button_label_widget, button_label_widget_label, button_widget, button_widget_label):
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

        # Assign button
        self.assign_event_button(button_widget, button_widget_label)

        # Retrieve shutter name from client.
        shutter_name = self.client.get_name()

        # Set value of label to shutter name.
        self.set_label(shutter_name, button_label_widget_label)

def run():
    if self.was_button_pressed(event_label=channel.name):