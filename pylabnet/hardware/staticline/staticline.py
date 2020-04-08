from pylabnet.utils.logging.logger import LogHandler


class Staticline():

    def __init__(self, name, logger,  hardware_module,  **kwargs):
        ''' TODO: Flesh this out

        This is the hgih level generic TTL-striggered hardware class. This
        instance should be the highest level instance with which TTL signals can be send out.
        Using an instance of o HardwareHandler, an instance of this class will be connected to an instance of a
        hardware class
        '''

        self.name = name

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Instanciate Hardware_handler
        self.hardware_handler = StaticlineHardwareHandler(hardware_module, self.log, **kwargs)

    def up(self):
        '''Set output to high'''
        self.hardware_handler.up()
        self.log.info(
            f"Staticline {self.name} set to high."
        )

    def down(self):
        '''Set output to low'''
        self.hardware_handler.down()
        self.log.info(
            f"Staticline {self.name} set to low."
        )



class StaticlineHardwareHandler():

    def setup_HDWAGDriver(self, **kwargs):
        for key, value in kwargs.items():
            self.log.info("%s == %s" %(key, value))

    def __init__(self, hardware_module, loghandler, **kwargs):
        '''TODO: Flesh this out

        Handler connecting hardware class to GenericTTLStaticline

        Main task of this instance is to define the device-specific function
        which should correspond to setting the staticline to high or low.
        '''
        self.hardware_module = hardware_module
        self.log = loghandler

        self.hardware_module_name = type(hardware_module).__name__

        # Dictionary listing all hardware modules which can address staticlines and their corresponding
        # setup functions.
        registered_staticline_modules = {
            'HDAWGDriver':  self.setup_HDWAGDriver
        }

        # Depending on which module is used, automatically call the specific setup function
        for module_name, setup_function in registered_staticline_modules.items():
            if self.hardware_module_name == module_name:
                setup_function(**kwargs)

