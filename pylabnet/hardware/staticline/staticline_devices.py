from abc import ABC, abstractmethod
from pylabnet.utils.helper_methods import load_config

class StaticLineHardwareHandler(ABC):
    '''Handler connecting hardware class to StaticLine instance

    Main task of this instance is to define the device-specific function
    which should correspond to setting the staticline to high or low, and
    to set up the hardware accordingly.

    :hardware_client: (object)
        Hardware client to be used to toggle the staticline.
    :log: (object)
        Instance of loghandler.
    :name: (str)
        Name of StaticLine instance.
    :config: (dict)
            Contains parameters needed to setup the hardware as a staticline.
    '''

    def __init__(self, name, log, hardware_client, config):
        self.name = name
        self.log = log
        self.hardware_client = hardware_client
        self.hardware_name = str(hardware_client.__class__).split('.')[-2]
        self.config = config

        self.setup()
        self.log.info(
            f"Setup of staticline {name} using module {self.hardware_name} successful."
            )

    @abstractmethod
    def setup(self):
        '''Sets up the staticline functions (e.g. up/down) in terms of the
        device client function calls. This is an abstract method as each
        subclass implements its own version based on its own functions.
        '''
        pass


class HDAWG(StaticLineHardwareHandler):

    def _HDAWG_toggle(self, newval):
        ''' Set DIO_bit to high or low

        :newval: Either 0 or 1 indicating the new output state.
        '''

        # Set correct mode to manual
        self.hardware_client.seti('dios/0/mode', 0)

        # Get current DIO output integer.
        current_output = self.hardware_client.geti('dios/0/output')

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

        self.hardware_client.seti('dios/0/output', new_output)

    def setup(self):
        ''' Setup a ZI HDAWG driver module to be used as a staticline toggle.

        :DIO_bit: Which bit to toggle, in decimal notation.
        '''

        # Retrieve arguments from keyword argument dictionary.

        assignment_dict = load_config('dio_assignment_global')

        DIO_bit = assignment_dict[self.config['bit_name']]

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
        current_config = self.hardware_client.geti('dios/0/drive')

        # Set new configuration by using the bitwise OR.
        new_config = current_config | toggle_bit
        self.hardware_client.seti('dios/0/drive', new_config)

        # Register up/down function.
        self.up = lambda: self._HDAWG_toggle(1)
        self.down = lambda: self._HDAWG_toggle(0)

        # Set correct mode to manual
        self.hardware_client.seti('dios/0/mode', 0)

class NiDaqMx(StaticLineHardwareHandler):

    def setup(self):
        '''Sets up the staticline functions (e.g. up/down) in terms of the
        device client function calls.
        '''

        # Retrieve arguments from configs, if not found apply default value.
        try:
            down_voltage = self.config['down_voltage']
        except KeyError:
            down_voltage = 0

        try:
            up_voltage = self.config['up_voltage']
        except KeyError:
            up_voltage = 3.3

        # Check if voltages are in bound.
        if not -10 <= down_voltage <= 10:
            self.log.error(f'Down voltage of {down_voltage} V is invalid, must be between -10 V and 10 V.')
        if not -10 <= up_voltage <= 10:
            self.log.error(f'Up voltage of {up_voltage} V is invalid, must be between -10 V and 10 V.')

        ao_output = self.config['ao_output']

        # Register up/down function.
        ao_output = self.config['ao_output']

        #Save the voltage in the hardware client to allow it to be shared between multiple Staticline Objects
        #This probably isn't the cleanest way to do this, its a bit hacky, in future should add an extended
        #staticline type "both" that combines analog and digital control
        self.hardware_client.up_voltage = up_voltage
        self.hardware_client.down_voltage =  down_voltage

        self.up = lambda: self.hardware_client.set_ao_voltage(ao_output, up_voltage)
        self.down = lambda: self.hardware_client.set_ao_voltage(ao_output, down_voltage)
        self.set_value = lambda value:self.hardware_client.set_ao_voltage(ao_output, value)

        # Set voltage to down.
        self.down()

        # Log successfull setup.
        self.log.info(f"NiDaq output {ao_output} successfully assigned to staticline {self.name}.")

class Toptica(StaticLineHardwareHandler):

    def setup(self):
        '''Sets up the staticline functions (e.g. up/down) in terms of the
        device client function calls.
        '''

        self.up = self.hardware_client.turn_on
        self.down = self.hardware_client.turn_off
        self.log.info(f'Toptica DLC PRO successfully assigned to staticline {self.name}')

class AbstractDevice(StaticLineHardwareHandler):

    def setup(self):
        '''Sets up the staticline functions (e.g. up/down) in terms of the
        device client function calls.
        '''

        self.up = lambda: self.hardware_client.up_function(self.config["ch"])
        self.down = lambda: self.hardware_client.down_function(self.config["ch"])
        self.set_value = lambda value: self.hardware_client.set_value_function(value, self.config["ch"])

################################################################################

registered_staticline_modules = {
    'zi_hdawg':  HDAWG,
    'nidaqmx_green': NiDaqMx,
    'toptica': Toptica,
    'abstract': AbstractDevice,
    'abstract2': AbstractDevice
}
