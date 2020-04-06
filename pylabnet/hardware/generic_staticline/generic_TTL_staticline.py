from pylabnet.utils.logging.logger import LogHandler


class GenericStaticline():

    def __init__(self, hardware_handler,  name, logger, init_state=False):
        ''' TODO: Flesh this out

        This is the hgih level generic TTL-striggered hardware class. This
        instance should be the highest level instance with which TTL signals can be send out.
        Using an instance of o HardwareHandler, an instance of this class will be connected to an instance of a
        hardware class
        '''

        self.name = name
        self.hardware_handler = hardware_handler

        # Instantiate log
        self.log = LogHandler(logger=logger)

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


class TTLHardwareHandler():

    def __init__(self, hardware_class, hardware_init_dict):
        '''TODO: Flesh this out

        Handler connecting hardware class to GenericTTLStaticline

        Main task of this instance is to define the device-specific function
        which should correspond to setting the staticline to high or low.
        '''
        self.hardware_class = hardware_class

        # Register up and down functions
        if hardware_class == A:
            self.up = hardware_class.somefunction
            self.down = hardware_class.some_other_function
        elif hardware_class == B:
            self.up = hardware_class.somefunction
            self.down = hardware_class.some_other_function
