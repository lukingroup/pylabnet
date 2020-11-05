import sys
import time
from PyQt5 import QtWidgets

import pylabnet.hardware.staticline.staticline as staticline
from pylabnet.gui.pyqt.gui_windowbuilder import GUIWindowFromConfig

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
        self.config = config
        self.config_dict = load_config(config, logger=self.log)
        self.initialize_drivers(staticline_clients, logger_client)

    def initialize_drivers(self, staticline_clients, logger_client):

        # Dictionary storing {device name : dict of staticline Drivers}
        self.staticlines = {}

        if staticline_clients is not None:
            for (hardware_type, device_id), hardware_client in staticline_clients.items():

                # Find the device entry in the config file by matching
                # hardware type with the client's.
                match = False
                for device_name, device_params in self.config_dict.items():

                    # Find the hardware client to have the correct hardware_type
                    # and device ID matching that specified in the config.
                    if (type(device_params) == dict and
                        'hardware_type' in device_params and
                        device_params['hardware_type'] == hardware_type):
                        # For configs that don't have IDs, assume it's a match.
                        if 'device_id' not in device_params:
                            match = True
                            break
                        elif device_params['device_id'] == device_id:
                            match = True
                            break

                # If no match in config file, we ignore this hardware client.
                if not match:
                    self.log.error(f"Hardware type {hardware_type}, ID = {device_id} has no matching entry in the config file.")
                    continue

                # If the device name is duplicated, we ignore this hardware client.
                if device_name in self.staticlines:
                    self.log.error(f"Device name {device_name} has been matched to multiple hardware clients."
                    "Subsequent matched hardware clients are ignored.")
                    continue
                # Create a dict to store the staticlines for this device
                else:
                    self.staticlines[device_name] = dict()

                # Iterate over all staticlines for that device and create a
                # driver instance for each line.
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

                    #If it has an initial default value, set that initially using set_value command
                    if "default" in device_params["staticline_configs"][staticline_idx]:
                        defaultValue = device_params["staticline_configs"][staticline_idx]["default"]
                        self.staticlines[device_name][staticline_name].set_value(defaultValue)

    def initialize_buttons(self):
        """Binds the function of each button of each device to the functions
        set up by each the device's staticline driver.
        """

        def set_value_fn(driver, text_widget):
            """ Helper function that we use to bind to text buttons for analog
            inputs, in order to avoid lambda scoping issues.
            """
            return lambda: driver.set_value(text_widget['AIN'].text())

        # Iterate through all devices in the config file
        for device_name, device_params in self.config_dict.items():
            if type(device_params) != dict:
                continue

            for staticline_idx in range(len(device_params["staticline_names"])):

                staticline_name = device_params["staticline_names"][staticline_idx]
                staticline_driver = self.staticlines[device_name][staticline_name]

                staticline_configs = device_params["staticline_configs"][staticline_idx]
                staticline_type = staticline_configs["type"]

                # Digital: Have an up and down button
                if staticline_type == 'digital':
                    widget = self.widgets[device_name][staticline_name]
                    widget['on'].clicked.connect(staticline_driver.up)
                    widget['off'].clicked.connect(staticline_driver.down)

                # Analog: "Apply" does something based on the text field value
                elif staticline_type == 'analog':
                    widget = self.widgets[device_name][staticline_name]
                    # Cannot use a lambda directly because this would lead to
                    # the values of staticline_driver and widget being referenced
                    # only at time of button click.
                    widget['apply'].clicked.connect(
                        set_value_fn(staticline_driver, widget))

                    #Set text of analog to default value
                    if "default" in staticline_configs:
                        #set initial text to initial value specified in config file
                        widget['AIN'].setText(str(staticline_configs["default"]))

                # Have both types of buttons
                elif staticline_type == 'adjustable_digital':
                    analog_widget = self.widgets[device_name][staticline_name+"_analog"]
                    digital_widget = self.widgets[device_name][staticline_name+"_digital"]
                    digital_widget['on'].clicked.connect(staticline_driver.up)
                    digital_widget['off'].clicked.connect(staticline_driver.down)
                    analog_widget['apply'].clicked.connect(
                        set_value_fn(staticline_driver, analog_widget))

                    #Set text of analog to default value
                    if "default" in staticline_configs:
                        #set initial text to initial value specified in config file
                        analog_widget['AIN'].setText(str(staticline_configs["default"]))
                else:
                    self.log.error(f'Invalid staticline type for device {device_name}. '
                                    'Should be analog or digital.')

    def run(self):
        """Starts up the staticline GUI and initializes the buttons. """

        # Starts up an application for the window
        self.app = QtWidgets.QApplication(sys.argv)

        # Create a GUI window with layout determined by the config file
        self.gui = GUIWindowFromConfig(config=self.config)
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
        config='staticline_config',
    )
    staticline_gui.run()

if __name__ == '__main__':
    main()
