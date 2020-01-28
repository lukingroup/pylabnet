from pylabnet.gui.pyqt import external_gui


class GUIHandler():
    """Generic Parent class for all GUI handlers"""

    def __init__(self,  client=None):
        """
        Instantiates generic GUI configurator

        :param client: (obj)
            instance of hardware client
        """

        self.gui = None
        self.is_running = False
        self._gui_connected = False
        self._gui_reconnect = False
        self.client = client

    def assign_gui(self, gui_client):
        """
        Assigns a GUI client to the GUI handler

        :param client:
            (obj) instance of GUI client
        """

        self.gui = gui_client

    def assign_client(self, client):
        """
        Assigns the hardware client to the GUI handler

        :param client:
            (obj) instance of hardware client
        """
        # Test
        # Test
        # TEst
        self.client = client
