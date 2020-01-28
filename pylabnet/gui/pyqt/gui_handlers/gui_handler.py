from pylabnet.gui.pyqt import external_gui


class GUIHandler():
    """Generic Parent class for all GUI handlers"""

    def __init__(self,  client=None):
        """
        Instantiates generic GUI configurator

        :param client: (obj)
            instance of hardware client
        """

        self.is_running = False  # Flag which lets us know if WlmMonitor is running
        self.is_paused = False  # Flag which tells us we have simply paused WlmMonitor operation
        self._gui_connected = False  # Flag which alerts if a GUI client has been connected successfully
        self._gui_reconnect = False  # Flag which tells us to try reconnecting to the GUI client

        self.gui = None
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

        self.client = client

    def protected_label()




