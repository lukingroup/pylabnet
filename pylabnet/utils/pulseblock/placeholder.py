import copy, operator
import numpy as np

class Placeholder(float):
    """ Used to hold a string placeholder for a variable that will be defined in
    the AWG code instead of beforehand. Contains an additional float value that
    acts as an offset and also a temp value for any comparisons or arithmetic
    expressions that need to be done before the actual value is resolved. 
    """

    default_values = {
            "offset_var" : 1, # Units of microseconds
            "dur_var" : 1, # Will be multipled by 1e-6 later
            "val_var" : 1,
            "amp_var" : 1,
            "stdev_var" : 0.1, # Will be multipled by 1e-6 later
            "mod_freq_var": 1e7,
            "mod_ph_var": 0
    }
    
    ##  Initialization
    def __new__(cls, name, val_offset=0):
        """ Initializes the float portion of the object. Float is immutable and
        thus we need to use __new__.  """

        # If all variables have 0 multiple - convert to float
        if type(name) == dict and (all(multiple == 0 for multiple in name.values()) 
                                   or len(name) == 0):
            return float(val_offset)
        return float.__new__(cls, val_offset)
    def __init__(self, name, val_offset=0): 
        if type(name) == str:
            self.name = {name: 1}
        elif type(name) == dict:
            self.name = name
        else:
            raise TypeError("Name should be str or dict.")
        self.name_str = "+".join(f"{multiple}*{name}" for name, multiple in self.name.items())

    ## Format
    def __str__(self):
        """ Representation of the object that can be evaluated once the name has
        a specified value. """
        return f"{self.name_str} + {float(self)}"
    def __format__(self, format_spec):
        return f"{self.name_str} + {float(self).__format__(format_spec)}"
    def int_str(self):
        """ String of the object with its value converted to int. """
        return f"{self.name_str} + {int(float(self))}"
    def round_val(self, num_dp=0):
        """ Object with its value rounded. """
        return Placeholder(self.name, round(float(self), num_dp))
    def int_val(self):
        """ Object with its value converted into int. """
        return Placeholder(self.name, int(float(self)))
    def var_str(self):
        """ Name of the object ignoring its value offset. """
        return self.name_str
    
    ## Arithmetic
    def __neg__(self):
        neg_name = {name: -multiple for name, multiple in self.name.items()}
        return Placeholder(neg_name, -float(self))

    def __add__(self, other):
        """ Adding combines their placeholder names and their offset values. """
        if isinstance(other, Placeholder):
            return Placeholder(self.combine_names(other, operator.add), float(self) + float(other))
        else:
            return Placeholder(self.name, float(self) + other)
    def __radd__(self, other):
        if isinstance(other, Placeholder):
            return self.__add__(other)
        else:
            return Placeholder(self.name, float(self) + other)

    def __sub__(self, other):
        """ Substraction utilizes addition and negation. """
        return self + (-other)
    def __rsub__(self, other):
        return other + (-self)

    def __mul__(self, other): 
        """ Multiplication combines their placeholder names and their offset values. """
        if isinstance(other, Placeholder):
            raise NotImplementedError
            # return Placeholder(f"{self.name} * {other.name}", float(self) * float(other))
        else:
            mult_name = {name: other*multiple for name, multiple in self.name.items()}
            return Placeholder(mult_name, float(self) * other)
    def __rmul__(self, other):
        if isinstance(other, Placeholder):
            raise NotImplementedError
            # return Placeholder(f"{other.name} * {self.name}", float(self) * float(other))
        else:
            mult_name = {name: other*multiple for name, multiple in self.name.items()}
            return Placeholder(mult_name, float(self) * other)

    ## Comparison
    def __eq__(self, other):
        if isinstance(other, Placeholder):
            return self.name == other.name and float(self) == float(other)
        else:
            return self.force_value() == other
    def __lt__(self, other):
        if isinstance(other, Placeholder): 
            return self.force_value() < other.force_value()
        else:
            return self.force_value() < other
    def __le__(self, other):
        return (self < other) or (self == other)
    def __gt__(self, other):
        if isinstance(other, Placeholder): 
            return self.force_value() > other.force_value()
        else:
            return self.force_value() > other
    def __ge__(self, other):
        return (self > other) or (self == other)
    def __hash__(self):
        return hash((frozenset(self.name.items()), float(self)))

    ## Copying
    def __copy__(self):
        return Placeholder(copy.copy(self.name), float(self))
    def __deepcopy__(self, memo=None):
        return Placeholder(copy.deepcopy(self.name), float(self))
    
    ## Helper
    def combine_names(self, other, op):
        """ Combine two Placeholders' names using an operator. Returns the new
        names dict. """
        new_name = copy.deepcopy(self.name)
        for other_name in other.name:
            if other_name in self.name:
                new_name[other_name] = op(new_name[other_name], other.name[other_name])
                # Delete entry if multiple is now 0.
                if new_name[other_name] == 0: 
                    del new_name[other_name]
            else:
                new_name[other_name] = op(0, other.name[other_name])
        return new_name

    def force_value(self):
        """ Force a value for evaluation by assuming a small positive value for 
        each placeholder. """
        # Values stores the multiple for each variable, their sum is equal to the
        # value from substituting 1 for each variable.
        return float(self) + 0.001 * sum(self.name.values())
    