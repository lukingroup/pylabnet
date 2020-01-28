from pylabnet.gui.pyqt.gui_handlers.gui_handler import GUIHandler


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

        # Assign label to widget.
        self.gui.assign_scalar(
            scalar_widget=button_label_widget,
            scalar_label=button_label_widget_name
        )

        # Retrieve shutter name from client.
        shutter_name = self.client.get_name()

        # Update shutter name.
        updated = False
        while not updated:
            try:
                self.gui.set_scalar(shutter_name, button_label_widget_name)
                updated = True
            except KeyError:
                pass

