from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase
from pylabnet.core.generic_server import GenericServer


class Driver():

    def __init__(self, name, logger,  hardware_module,  **kwargs):
        '''High level staticline class.

        This class is used in conjunction with hardware modules to send out digital
        signals ('voltage low' and 'voltage high'). This top level class is hardware agnostic.
        With the use of a StaticLineHardwareHandler, this class will be associated with the necessary
        setup functions and output functions of a hardware module.

        :name: A easily recognizable name for this staticline, ideally referring to the device being controlled
            by it, e.g. 'Shutter 1'.
        :logger: An instance of a LogClient.
        :hardware_module: An instance of a hardware module. Based on this, the corresponsind setup function is automatically
            called.
        '''

        self.name = name

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Instantiate Hardware_handler
        self.hardware_handler = StaticLineHardwareHandler(
            hardware_module,
            self.log, name,
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


class StaticLineHardwareHandler():

    def _HDAWG_toggle(self, newval):
        ''' Set DIO_bit to high or low

        :newval: Either 0 or 1 indicating the new output state.
        '''

        # Get current DIO output integer.
        current_output = self.hardware_module.geti('dios/0/output')

        if newval == 0:
            # E.g., for DIO-bit 3: 1111 .... 1110111
            DIO_bit_bitshifted = ~(0b1 << self.DIO_bit)

            # Binary AND generates new output.
            new_output = current_output & DIO_bit_bitshifted

        elif newval == 1:
            # E.g., for DIO-bit 3: 0000 ... 0001000
            DIO_bit_bitshifted = (0b1 << self.DIO_bit)

            # Binary OR generates new output.
            new_output = current_output | DIO_bit_bitshifted

        self.hardware_module.seti('dios/0/output', new_output)

    def _setup_HDWAGDriver(self, **kwargs):
        ''' Setup a ZI HDAWG driver module to be used as a staticline toggle.

        :DIO_bit: Which bit to toggle, in decimal notation.
        '''

        # Retrieve arguments from keyword argument dictionary.
        DIO_bit = kwargs['DIO_bit']

        # Drive 8-bit bus containing DIO_bit to be toggled.
        # Note that the buses are enabled by using the decimal equivalent
        # of a binary number indicating which bus is driven:
        # 1101 = 11 corresponds to driving bus 1, 2, and 4.

        if DIO_bit in range(8):
            toggle_bit = 1  # 1000
        elif DIO_bit in range(8, 16):
            toggle_bit = 2  # 0100
        elif DIO_bit in range(16, 24):
            toggle_bit = 4  # 0010
        elif DIO_bit in range(24, 32):
            toggle_bit = 8  # 0001
        else:
            self.log.error(f"DIO_bit {DIO_bit} invalid, must be in range 0-31.")

        self.DIO_bit = DIO_bit
        self.log.info(f"DIO_bit {DIO_bit} successfully assigned to staticline {self.name}.")

        # Read in current configuration of DIO-bus.
        current_config = self.hardware_module.geti('dios/0/drive')

        # Set new configuration by using the bitwise OR.
        new_config = current_config | toggle_bit
        self.hardware_module.seti('dios/0/drive', new_config)

        # Register up/down function.
        self.up = lambda: self._HDAWG_toggle(1)
        self.down = lambda: self._HDAWG_toggle(0)

    def _setup_NiDaqMxDriver(self, **kwargs):

        # Retrieve arguments from keyword argument dictionary,
        # if not found apply default value.
        try:
            down_voltage = kwargs['down_voltage']
        except KeyError:
            down_voltage = 0

        try:
            up_voltage = kwargs['up_voltage']
        except KeyError:
            up_voltage = 3.3

        # Check if voltages are in bound.
        if not -10 <= down_voltage <= 10:
            self.log.error(f'Down voltage of {down_voltage} V is invalid, must be between -10 V and 10 V.')
        if not -10 <= up_voltage <= 10:
            self.log.error(f'Up voltage of {up_voltage} V is invalid, must be between -10 V and 10 V.')

        ao_output = kwargs['ao_output']

        # Register up/down function.
        ao_output = kwargs['ao_output']
        self.up = lambda: self.hardware_module.set_ao_voltage(ao_output, up_voltage)
        self.down = lambda: self.hardware_module.set_ao_voltage(ao_output, down_voltage)

        # Set voltage to down.
        self.down()

        # Log successfull setup.
        self.log.info(f"NiDaq {self.hardware_module.dev} output {ao_output} successfully assigned to staticline {self.name}.")

    def __init__(self, hardware_module, loghandler, name, **kwargs):
        '''Handler connecting hardware class to StaticLine instance

        Main task of this instance is to define the device-specific function
        which should correspond to setting the staticline to high or low, and
        to set up the hardware accordingly.

        :hardware_module: Hardware module to be used to toggle the staticline.
        :loghandler: Instance of loghandler.
        :name: Name of StaticLine instance.
        :**kwargs: Additional keyword arguments which depending on the hardware module
            contain values needed to setup the hardware as a staticline.
        '''
        self.hardware_module = hardware_module
        self.name = name
        self.log = loghandler

        # Read string of module name (e.g. 'HDAWGDriver').
        self.hardware_module_name = str(hardware_module.__class__).split('.')[-2]

        # Dictionary listing all hardware modules which can address
        # staticlines and their corresponding setup functions.
        registered_staticline_modules = {
            'zi_hdawg':  self._setup_HDWAGDriver,
            'nidaqmx_card': self._setup_NiDaqMxDriver
        }

        # Check if hardware module is registered.
        if self.hardware_module_name not in registered_staticline_modules.keys():
            valid_modules = list(registered_staticline_modules.keys())
            error_msg = f"Setup of staticline using module {self.hardware_module_name} failed. Compatible modules are {valid_modules}."
            self.log.error(error_msg)

        # Depending on which module is used,
        # automatically call the hardware-specific setup function.
        for module_name, setup_function in registered_staticline_modules.items():

            if self.hardware_module_name == module_name:

                # Call hardware specific setup function.
                setup_function(**kwargs)

                self.log.info(
                    f"Setup of staticline {name} using module {module_name} successful."
                )


class Service(ServiceBase):

    def exposed_up(self):
        return self._module.up()

    def exposed_down(self):
        return self._module.down()

    def exposed_get_name(self):
        return self._module.get_name()


class Client(ClientBase):

    def up(self):
        return self._service.exposed_up()

    def down(self):
        return self._service.exposed_down()

    def get_name(self):
        return self._service.exposed_get_name()


def launch(**kwargs):
    """ Connects to a NI DAQ as staticline

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    import pylabnet.hardware.ni_daqs.nidaqmx_card as nidaqmx

    device_name = 'cDAQ1Mod1'
    daq = nidaqmx.Driver(device_name=device_name, logger=kwargs['logger'])

    test_staticline = Driver(
        name='Test staticline',
        logger=kwargs['logger'],
        hardware_module=daq,
        ao_output='ao2',

        down_voltage=0,
        up_voltage=3.3,
    )

    # Instantiate Server
    # Staticline server
    staticline_service = Service()
    staticline_service.assign_module(module=test_staticline)
    staticline_service.assign_logger(logger=kwargs['logger'])
    staticline_service_server = GenericServer(
        service=staticline_service,
        host='localhost',
        port=kwargs['port']
    )

    staticline_service_server.start()