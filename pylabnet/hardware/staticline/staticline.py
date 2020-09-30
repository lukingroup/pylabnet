from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.hardware.staticline.staticline_devices import StaticLineDevice

class Driver():

    def __init__(self, name, logger,  hardware_client, hardware_handler, **kwargs):
        '''High level staticline class.

        This class is used in conjunction with hardware modules to send out digital
        signals ('voltage low' and 'voltage high'). This top level class is hardware agnostic.
        With the use of a StaticLineHardwareHandler, this class will be associated with the necessary
        setup functions and output functions of a hardware module.

        :name: A easily recognizable name for this staticline, ideally referring to the device being controlled
            by it, e.g. 'Shutter 1'.
        :logger: An instance of a LogClient.
        :hardware_client: An instance of a hardware module. 
        :hardware_handler: Class name of hardware handler to be used.
        '''

        self.name = name

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Check that the provided class is a valid StaticLine class
        if not issubclass(hardware_handler, StaticLineDevice):
            error_msg = f"Setup of staticline using module {hardware_handler.__name__} failed. "
            error_msg += "Compatible modules are found in staticline_devices.py."
            self.log.error(error_msg)

        # Instantiate Hardware_handler
        self.hardware_handler = hardware_handler(
            hardware_client,
            self.log, 
            name,
            **kwargs
        )

    def up(self):
        '''Set output to high.'''
        self.hardware_handler.up()
        self.log.info(
            f"Staticline {self.name} set to high."
        )

    def down(self):
        '''Set output to low.'''
        self.hardware_handler.down()
        self.log.info(
            f"Staticline {self.name} set to low."
        )

    def get_name(self):
        return self.name