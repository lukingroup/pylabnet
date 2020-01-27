from pylabnet.scripts.gui_configurators.configurator import GUIConfigurator


class ShutterGUIConfigurator(GUIConfigurator):

    def __init__(self, client=None):
        """
        Instantiates shutter gui

        :param shutter_client: (obj)
            instance of shutter client
        """

        # Instanciate generic GUIConfigurator
        GUIConfigurator.__init__(self, client=None)

    def set_labels(self):
        """ Correctly labels the shutter toggle button with name of shutter"""

        # Retrieve shutter name from client.
        shutter_name = self.client.get_name()

        # Assign shutter name to pushbutton widget.
        widget = 'pushButton1label'
        label = shutter_name

        self.gui.assign_scalar(widget, label)
