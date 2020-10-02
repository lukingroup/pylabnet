from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.staticline.staticline_devices import registered_staticline_modules

class Driver():

    def __init__(self, name, logger,  hardware_client, hardware_type, config):
        '''High level staticline class.

        This class is used in conjunction with hardware modules to send out digital
        signals ('voltage low' and 'voltage high'). This top level class is hardware agnostic.
        With the use of a StaticLineHardwareHandler, this class will be associated 
        with the necessary setup functions and output functions of a hardware module.

        :name:(str) 
            A easily recognizable name for this staticline, ideally referring to 
            the device being controlled by it, e.g. 'Shutter 1'.
        :logger: (object)
            An instance of a LogClient.
        :hardware_client: (object) 
            An instance of a hardware Client. 
        :hardware_type: (str)
            Name of the hardware to be controlled, naming is determined by the
            device server name.
        :config: (dict)
            Contains parameters needed to setup the hardware as a staticline.
        '''

        self.name = name
        self.log = LogHandler(logger=logger)

        # Check that the provided class is a valid StaticLine class
        if hardware_type not in registered_staticline_modules:
            self.log.error(
                f"Setup of staticline using module {hardware_type} failed.\n"
                f"Compatible modules are: {registered_staticline_modules.keys()}")

        # Acquire the correct handler for the hardware type
        hardware_handler = registered_staticline_modules[hardware_type]

        # Instantiate hardware handler. The hardware_handler will handle any
        # calls to the staticline functions like up/down.
        self.hardware_handler = hardware_handler(
            name=name, 
            log=self.log, 
            hardware_client=hardware_client, 
            config=config
        )

    def up(self):
        '''Set output to high.'''
        self.hardware_handler.up()
        self.log.info(f"Staticline {self.name} set to high.")

    def down(self):
        '''Set output to low.'''
        self.hardware_handler.down()
        self.log.info(f"Staticline {self.name} set to low.")

    def set_value(self, value):
        '''Set output to a specified value.'''
        self.hardware_handler.set_value(value)
        self.log.info(f"Staticline {self.name} set to {value}.")

    def get_name(self):
        return self.name