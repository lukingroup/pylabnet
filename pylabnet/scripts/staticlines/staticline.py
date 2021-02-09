import sys
import time
import socket
import ctypes
import os
from PyQt5 import QtWidgets, QtGui

import pylabnet.hardware.staticline.staticline as staticline
from pylabnet.gui.pyqt.gui_windowbuilder import GUIWindowFromConfig

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import get_os, get_ip, unpack_launcher, load_script_config, find_client


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

    def __init__(self, config, staticline_clients=None, logger_client=None, host=None, port=None):

        self.log = LogHandler(logger=logger_client)
        self.config = config
        self.host=host
        self.port=port
        self.config_dict = load_script_config('staticline', config, logger=self.log)
        self.initialize_drivers(staticline_clients, logger_client)

    def initialize_drivers(self, staticline_clients, logger_client):

        # Dictionary storing {device name : dict of staticline Drivers}
        self.staticlines = {}


        for device_name, device_params in self.config_dict['lines'].items():
            # If the device name is duplicated, we ignore this hardware client.
            if device_name in self.staticlines:
                self.log.error(f"Device name {device_name} has been matched to multiple hardware clients."
                "Subsequent matched hardware clients are ignored.")
                continue
            # Create a dict to store the staticlines for this device
            else:
                self.staticlines[device_name] = dict()

            hardware_type=device_params['hardware_type']
            hardware_config=device_params['config_name']

            #Try to find if we have a matching device client in staticline_clients
            try:
                hardware_client = find_client(staticline_clients, self.config_dict, hardware_type, hardware_config, logger_client)
            except NameError:
                logger_client.error('No staticline device found for device name: '  + device_name)


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
                    sl_type = device_params["staticline_configs"][staticline_idx]['type']
                    if (sl_type == 'analog'):
                        self.staticlines[device_name][staticline_name].set_value(defaultValue)
                    elif (sl_type == 'adjustable_digital'):
                        self.staticlines[device_name][staticline_name].set_dig_value(defaultValue)



    def initialize_buttons(self):
        """Binds the function of each button of each device to the functions
        set up by each the device's staticline driver.
        """

        def set_value_fn(driver, text_widget):
            """ Helper function that we use to bind to text buttons for analog
            inputs, in order to avoid lambda scoping issues.
            """
            return lambda: driver.set_value(text_widget['AIN'].text())

        def set_dig_value_fn(driver, text_widget):
            """ Helper function that we use to bind to text buttons for adjustable digital
            inputs, in order to avoid lambda scoping issues.
            """

            return lambda: driver.set_dig_value(text_widget['AIN'].text())

        # Iterate through all devices in the config file
        for device_name, device_params in self.config_dict['lines'].items():
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
                        self.gui.upd_cur_val(device_name=device_name, staticline_name=staticline_name)
                # Have both types of buttons
                elif staticline_type == 'adjustable_digital':
                    analog_widget = self.widgets[device_name][staticline_name+"_analog"]
                    digital_widget = self.widgets[device_name][staticline_name+"_digital"]
                    digital_widget['on'].clicked.connect(staticline_driver.up)
                    digital_widget['off'].clicked.connect(staticline_driver.down)
                    analog_widget['apply'].clicked.connect(
                        set_dig_value_fn(staticline_driver, analog_widget))

                    #Set text of analog to default value
                    if "default" in staticline_configs:
                        #set initial text to initial value specified in config file
                        analog_widget['AIN'].setText(str(staticline_configs["default"]))
                        self.gui.upd_cur_val(device_name=device_name, staticline_name=staticline_name+"_analog")
                else:
                    self.log.error(f'Invalid staticline type for device {device_name}. '
                                    'Should be analog or digital.')

    def run(self):
        """Starts up the staticline GUI and initializes the buttons. """

        # Starts up an application for the window
        if get_os() == 'Windows':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setWindowIcon(
            QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
        )

        # Create a GUI window with layout determined by the config file
        self.gui = GUIWindowFromConfig(config=self.config, host=self.host, port=self.port)
        self.gui.show()
        self.widgets = self.gui.widgets

        # Binds the function of the buttons to the staticline Driver functions
        self.initialize_buttons()

        self.app.exec_()


def launch(**kwargs):
    """Launches the script."""

    logger = kwargs['logger']
    clients = kwargs['clients']

    try:
        staticline_gui = StaticLineGUIGeneric(
            config=kwargs['config'],
            staticline_clients=clients,
            logger_client=logger,
            host=get_ip(),
            port=kwargs['server_port']
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
