import sys
import time 
from PyQt5 import QtWidgets

import pylabnet.hardware.staticline.staticline as staticline
from pylabnet.gui.pyqt.gui_windowbuilder_test import GUIWindowFromConfig

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, load_config


class StaticLineGUIGeneric():
    """Static Line GUI

    :config: (str)
        Path to a config file specifying the staticlines to be included in this
        GUI.
    :staticline_clients: (dict)
        Dictionary of {hardware type (str) : instance of device Client}. The 
        hardware type must be same as those listed in the config files.
    :logger_client: (object)
        Instance of logger client.
    """

    def __init__(self, config, staticline_clients=None, logger_client=None):

        self.log = LogHandler(logger=logger_client)
        self.config_path = config
        self.config = load_config(config, logger=self.log)
        self.initialize_drivers(staticline_clients, logger_client)

    def initialize_drivers(self, staticline_clients, logger_client):

        # Dictionary storing {device name : instance of staticline Driver}
        self.staticlines = {}

        if staticline_clients is not None:
            for hardware_type, hardware_client in staticline_clients.items():
                
                # Find the device entry in the config file by matching the 
                # hardware type with the clients in the client list.
                # This requires the hardware_type to match the device server 
                # names as listed in server_req in the Launcher.
                # TODO: only works with 1 device per hardware_type.
                for device_params in self.config.values():
                     if device_params['hardware_type'] == hardware_type:
                         break
                
                device_name = device_params['name']
                self.staticlines[device_name] = dict()

                for staticline_idx in range(len(device_params["staticline_names"])):

                    staticline_name = device_params["staticline_names"][staticline_idx]

                    # Store the staticline driver under the specified device name
                    self.staticlines[device_name][staticline_name] = staticline.Driver(
                        name=device_name + "_" + staticline_name,
                        logger=logger_client,
                        hardware_client=hardware_client,
                        hardware_type=hardware_type,
                        config=device_params["staticline_configs"][staticline_idx]
                    )

    def initialize_buttons(self):
        """Binds the function of each button of each device to the functions
        set up by each the device's staticline driver.
        """

        # Iterate through all devices in the config file
        for device in self.config.values():

            device_name = device['name']

            for staticline_idx in range(len(device["staticline_names"])):

                staticline_name = device["staticline_names"][staticline_idx]
                staticline_driver = self.staticlines[device_name][staticline_name]

                staticline_configs = device["staticline_configs"][staticline_idx]
                staticline_type = staticline_configs["type"]
                
                widget = self.widgets[device_name][staticline_name]

                # Digital: Have an up and down button
                if staticline_type == 'digital':
                    widget['on'].clicked.connect(staticline_driver.up)
                    widget['off'].clicked.connect(staticline_driver.down)

                # Analog: "Apply" does something based on the text field value
                elif staticline_type == 'analog':

                    widget['apply'].clicked.connect(lambda:
                        staticline_driver.set_value(widget['AIN'].text()))
                    
                else:
                    self.log.error(f'Invalid staticline type for device {device_name}. '
                                    'Should be analog or digital.')

    def run(self):
        """Starts up the staticline GUI and initializes the buttons. """

        # Starts up an application for the window
        self.app = QtWidgets.QApplication(sys.argv)
        
        # Create a GUI window with layout determined by the config file
        self.gui = GUIWindowFromConfig(config=self.config_path)
        self.gui.show()
        self.widgets = self.gui.widgets

        # Binds the function of the buttons to the staticline Driver functions
        self.initialize_buttons()
        
        self.app.exec_()


def launch(**kwargs):
    """Launches the script."""

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    try:
        staticline_gui = StaticLineGUIGeneric(
            config=kwargs['config'],
            staticline_clients=clients,
            logger_client=logger,
        )
    except KeyError:
        logger.error('Please make sure the module names for required servers and GUIS are correct.')

    staticline_gui.run()

def main():
    """Main function for debugging. """

    staticline_gui = StaticLineGUIGeneric(
        config='test_config_sl',
    )
    staticline_gui.run()

if __name__ == '__main__':
    main()
