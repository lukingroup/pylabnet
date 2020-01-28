from pylabnet.gui.pyqt.gui_handlers.gui_handler import GUIHandler
from pylab.utils.decorators.gui_decorators import protected_widget_change

class ShutterGUIHandler(GUIHandler):

    def __init__(self, client=None):
        """
        Instantiates shutter gui

        :param shutter_client: (obj)
            instance of shutter client
        """

        # Instanciate parent class.
        super(ShutterGUIHandler, self).__init__(client)

    def initialize_label(self, button_label_widget, button_label_widget_name):
        """ Initialize label to shutter name

        :button_label_widget: (string)
            widget name of label of button toggling the shutter
        :button_label_widget_label: (string)
            widget name of label of button toggling the shutter
        """

        @protected_widget_change
        self.gui.assign_label(button_label_widget, button_label_widget_name)

        # Retrieve shutter name from client.
        shutter_name = self.client.get_name()
