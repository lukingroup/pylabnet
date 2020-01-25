class GUIConfigurator():
    """Generic Parent class for all GUI configurators"""

    def __init__(self,  client=None):
        """
        Instantiates generic GUI configurator

        :param client: (obj)
            instance of shutter client
        """

        self.gui = None
        self.is_running = False
        self._gui_connected = False
        self._gui_reconnect = False
        self.client = client

    def assign_gui(self, gui_client):
        """
        Assigns a GUI client to the ShutterGUI

        :param client:
            (obj) instance of GUI client
        """

        self.gui = gui_client

    def assign_client(self, client):
        """
        Assigns the wlm Client to the WlmMonitor module

        :param wlm_client:
            (obj) instance of Client of High-Finesse wavemeter
        """

        self.client = client
