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

    def check_keyword_args(self, required_kwargs, **kwargs):
        ''' Checks if the provided keywords contain the required ones

        Provides an error message to the log handler check fails.

        :required_kwargs: List of strings listing the names of
            the required keyword parameters.
        :**kwargs: The keyword arguments to be checked
        '''

        for required_kwarg in required_kwargs:
            if required_kwarg not in kwargs.keys():

                error_msg = f'Need to provide the following keyword argument to initialize {self.hardware_module_name}: {required_kwarg}'
                self.log.error(error_msg)
                raise Exception(error_msg)

    def setup_HDWAGDriver(self, **kwargs):
        ''' Setup a ZI HDAWG driver module to be used as a staticline toogle

        :DIO_bit: Which bit to toggle
        '''

        # Explicitly specify which keyword arguments are needed
        necessary_kwargs = ['DIO_bit']

        # Check if all keyword arguments are given.
        check_keyword_args(necessary_kwargs, **kwargs):

    def __init__(self, hardware_module, loghandler, **kwargs):
        '''TODO: Flesh this out

        Handler connecting hardware class to GenericTTLStaticline

        Main task of this instance is to define the device-specific function
        which should correspond to setting the staticline to high or low.
        '''
        self.hardware_module = hardware_module
        self.log = loghandler

        # Read string of module name (e.g. 'HDAWGDriver').
        self.hardware_module_name = type(hardware_module).__name__

        # Dictionary listing all hardware modules which can address
        # staticlines and their corresponding setup functions.
        registered_staticline_modules = {
            'HDAWGDriver':  self.setup_HDWAGDriver
        }

        # Check if hardware module is registered.
        if self.hardware_module_name not in registered_staticline_modules.keys():
            valid_modules = list(registered_staticline_modules.keys())
            error_msg = f"Setup of staticline using module {self.hardware_module_name} failed. Compatible modules are {valid_modules}."
            self.log.error(error_msg)
            raise Exception(error_msg)

        # Depending on which module is used,
        # automatically call the hardware-specific setup function.
        setup_successful = False
        for module_name, setup_function in registered_staticline_modules.items():

            if self.hardware_module_name == module_name:

                # All setup function need to output a boolean indicating the
                # setup success.
                setup_function(**kwargs)

                self.log.info(
                    f"Setup of staticline using module {module_name} successful."
                )

