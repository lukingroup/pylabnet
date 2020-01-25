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
