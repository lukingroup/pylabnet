from simpleeval import simple_eval, NameNotDefined
from datetime import datetime
import uuid


import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb


class PulseblockConstructor():
    """Container Class which stores all necessary information to compile full Pulseblock,
    while retaining the ability to change variables and easy save/load functionality.
    """

    def __init__(self, name, log, var_dict):

        self.name = name
        self.log = log

        self.var_dict = var_dict
        self.pulse_specifiers = []
        self.pulseblock = None

    def resolve_value(self, input_val):
        """ Return value of input_val.

        If input_val is either already not a string, in which case it will be returned.
        Alternatively, the input value could be a variable, as defined in the keys
        in the var_dict. In this case the value associated with this variable will be
        returned.
        :input: (str / float / bool etc) Variable value or variable string.
        """

        if type(input_val) is not str:
            return input_val
        else:
            try:
                return simple_eval(input_val, names=self.var_dict)
            except KeyError:
                self.log.error(f"Could not resolve variable '{input_val}'.")
    
    def append_value_to_dict(self, search_dict, key, append_dict, fn=None, new_key=None):
        """ Append a searched value from a search dictionary to a separate 
        dictionary, if the given key exists.

        :search_dict: search_dict (dict) Dictionary to search the key for
        :key: (str) Key to query the search dictionary using
        :append_dict: (dict) Value of the found key will be appended into this
            dictionary if it exists
        :fn: (function, optional) Function to be applied to the found value 
        :new_key: (str, optional) New key that the found value will be added 
            to in the append_dict. If not provided, it will use the old key
        """

        if key in search_dict:
            value = self.resolve_value(search_dict[key])

            if fn is not None:
                value = fn(value)
            if new_key is None:
                new_key = key

            append_dict[new_key] = value

    def compile_pulseblock(self):
        """ Compiles the list of pulse_specifiers and var dists into valid
        Pulseblock.
        """

        pulseblock = pb.PulseBlock(name=self.name)

        for i, pb_spec in enumerate(self.pulse_specifiers):
            
            var_dict = pb_spec.pulsevar_dict
            arg_dict = {}

            # Extract parameters from the pulsevar dict
            offset = self.resolve_value(pb_spec.offset)  * 1e-6
            arg_dict["ch"] = pb_spec.channel
            arg_dict["dur"] = self.resolve_value(pb_spec.dur) * 1e-6

            self.append_value_to_dict(var_dict, "amp", arg_dict)
            self.append_value_to_dict(var_dict, "freq", arg_dict)
            self.append_value_to_dict(var_dict, "ph", arg_dict)
            self.append_value_to_dict(var_dict, "stdev", arg_dict, fn=lambda x: 1e-6*x)
            self.append_value_to_dict(var_dict, "mod", arg_dict)
            self.append_value_to_dict(var_dict, "mod_freq", arg_dict)
            self.append_value_to_dict(var_dict, "mod_ph", arg_dict)

            supported_pulses = {
                "PTrue" : po.PTrue,
                "PSin" : po.PSin,
                "PGaussian" : po.PGaussian,
                "PConst" : po.PConst
            }

            # Construct single pulse.
            if pb_spec.pulsetype in supported_pulses:
                pulse = supported_pulses[pb_spec.pulsetype](**arg_dict)
            
            else:
                pulse = None
                self.log.warn(f"Found an unsupported pulse type {pb_spec.pulsetype}")


            # Insert pulse to correct position in pulseblock.
            if pb_spec.tref == "Absolute":
                pb_dur = pulseblock.dur
                pulseblock.append_po_as_pb(
                    p_obj=pulse,
                    offset=-pb_dur+offset
                )

            elif pb_spec.tref == "After Last Pulse":
                pulseblock.append_po_as_pb(
                    p_obj=pulse,
                    offset=offset
                )

            elif pb_spec.tref == "With Last Pulse":

                # Retrieve previous pulseblock:
                if i != 0:
                    previous_pb_spec = self.pulse_specifiers[i-1]
                else:
                    raise ValueError(
                       "Cannot chose timing reference 'With Last Pulse' for first pulse in pulse-sequence."
                    )

                # Retrieve duration of previous pulseblock.
                prev_dur = self.resolve_value(previous_pb_spec.dur) * 1e-6
                pulseblock.append_po_as_pb(
                    p_obj=pulse,
                    offset=-prev_dur + offset
                )

        self.pulseblock =  pulseblock

    def get_dict(self):
        """Get dictionary representing the pulseblock."""

        # Compile
        self.compile_pulseblock()
        pb_dictionary = {}
        pb_dictionary["name"] = self.name
        pb_dictionary["dur"] = self.pulseblock.dur
        pb_dictionary["timestamp"] = datetime.now().strftime("%d-%b-%Y_%H_%M_%S")
        pb_dictionary["var_dict"] =  self.var_dict
        pb_dictionary["pulse_specifiers_dicts"] = [ps.get_dict() for ps in self.pulse_specifiers]
        self.log.info(str(pb_dictionary))
        return pb_dictionary

    def load_as_dict(self):
        pass


class PulseSpecifier():
    """Container storing info pully specifiying pulse within pulse sequence."""

    def __init__(self, channel, pulsetype, pulsetype_name, is_analog):
        self.channel = channel
        self.pulsetype = pulsetype
        self.pulsetype_name = pulsetype_name
        self.is_analog = is_analog

        # Generate random unique identifier.
        self.uid = uuid.uuid1()

    def set_timing_info(self, offset, dur, tref):
        self.offset = offset
        self.dur = dur
        self.tref = tref

    def set_pulse_params(self, pulsevar_dict):
        self.pulsevar_dict = pulsevar_dict

    def get_printable_name(self):
        return f"{self.channel.capitalize()} ({self.pulsetype_name})"

    # Reader friendly string return.
    def __str__(self):
        return self.get_printable_name()

    def get_dict(self):
        """Store all member variables as dictionary for easy saving."""
        pulse_specifier_dict = {}
        pulse_specifier_dict['pulsetype'] = self.pulsetype
        pulse_specifier_dict['channel'] = self.channel
        pulse_specifier_dict['is_analog'] = self.is_analog

        pulse_specifier_dict['dur'] = self.dur
        pulse_specifier_dict['offset'] = self.offset
        pulse_specifier_dict['tref'] = self.tref
        pulse_specifier_dict['pulse_vars'] = self.pulsevar_dict
        pulse_specifier_dict['name'] = self.pulsetype_name

        return pulse_specifier_dict
