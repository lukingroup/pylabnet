import numpy as np


# Base classes ----------------------------------------------------------------

class PulseBase:
    """ Base class for Pulse objects
    """

    def __init__(self, ch, dur, t0=0):
        """ Base class for Pulse object

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        """

        self.ch = ch
        self.t0 = t0
        self.dur = dur


class DfltPulseBase:
    """ Base class for DfltPulse objects
    """

    def __eq__(self, other):
        raise NotImplementedError(
            'Every default pulse class has to define __eq__() method. \n'
            'Reason: during insert_pb() call, a check for conflicts between '
            'default pulse objects on the overlapping channels is performed'
            'by direct comparison operation.'
        )

class Placeholder(float):
    """ Used to hold a string placeholder for a variable that will be defined in
    the AWG code instead of beforehand. Contains an additional float value that
    acts as an offset and also a temp value for any comparisons or arithmetic
    expressions that need to be done before the actual value is resolved. 
    """

    def __new__(self, name, val_offset=0):
        """ Initializes the float portion of the object. Float is immutable and
        thus we need to use __new__.  """
        return float.__new__(self, val_offset)
    def __init__(self, name, val_offset=0):
        self.name = name
    def __str__(self):
        """ Reprensetation of the object that can be evaluated once the name has
        a specified value. """
        return f"{self.name} + {float(self)}"
    def __format__(self, format_spec):
        return f"{self.name} + {float(self).__format__(format_spec)}"

    def __add__(self, other):
        """ Adding combines their placeholder names and their offset values. """
        if isinstance(other, Placeholder):
            return Placeholder(f"{self.name} + {other.name}", float(self) + float(other))
        else:
            return Placeholder(self.name, float(self) + other)
    def __radd__(self, other):
        if isinstance(other, Placeholder):
            return Placeholder(f"{other.name} + {self.name}", float(self) + float(other))
        else:
            return Placeholder(self.name, float(self) + other)

    def __sub__(self, other):
        """ Adding combines their placeholder names and their offset values. 
        If they have the same name, their difference is just a simple number! """
        if isinstance(other, Placeholder):
            if self.name == other.name:
                return float(self) - float(other)
            else:
                return Placeholder(f"{self.name} - {other.name}", float(self) - float(other))
        else:
            return Placeholder(self.name, float(self) - other)
        # return Placeholder(self.name, float(self) - other)
    def __rsub__(self, other):
        if isinstance(other, Placeholder):
            if self.name == other.name:
                return float(other) - float(self)
            else:
                return Placeholder(f"{other.name} - {self.name}", float(other) - float(self))
        else:
            return Placeholder(self.name, other - float(self))
        # return Placeholder(self.name, other - float(self))

    def __mul__(self, other): 
        """ Multiplication combines their placeholder names and their offset values. """
        if isinstance(other, Placeholder):
            return Placeholder(f"{self.name} * {other.name}", float(self) * float(other))
        else:
            return Placeholder(self.name, float(self) * other)
    def __rmul__(self, other):
        if isinstance(other, Placeholder):
            return Placeholder(f"{other.name} * {self.name}", float(self) * float(other))
        else:
            return Placeholder(self.name, float(self) * other)

    def __copy__(self):
        return Placeholder(self.name, float(self))
    def __deepcopy__(self, memo=None):
        return Placeholder(self.name, float(self))

    def int_str(self):
        """ String of the object with its value converted to int. """
        return f"{self.name} + {int(float(self))}"
    def round_val(self):
        """ Object with its value rounded. """
        return Placeholder(self.name, np.round(float(self)))
    def var_str(self):
        """ Name of the object ignoring its value offset. """
        return self.name


# Pulse classes ---------------------------------------------------------------

# Digital Pulse classes --------------------------------------------------------

class PTrue(PulseBase):
    """ Pulse: Boolean True
    """

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

        # Define an automatic default.
        self.auto_default = DFalse()
        self.is_analog = False


    def __str__(self):
        return 'True'

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=bool)) array of samples
        """

        return np.full(len(t_ar), True)


class PFalse(PulseBase):
    """ Pulse: Boolean False
    """

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

        # Define an automatic default.
        self.auto_default = DTrue()
        self.is_analog = False

    def __str__(self):
        return 'False'

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=bool)) array of samples
        """

        return np.full(len(t_ar), False)

# Analog Pulse classes ---------------------------------------------------------

class PSin(PulseBase):
    """ Pulse: Sine
    """

    def __init__(self, ch, dur, t0=0, amp=0, freq=0, ph=0, 
                mod=False, mod_freq=0, mod_ph=0,
                iq=False, iq_params=None):
        """ Construct Sin Pulse object

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param amp: (opt, np.float32) amplitude (zero-to-peak)
        :param freq: (opt, np.float32) frequency (linear, without 2*pi)
        :param ph: (opt, np.float32) phase (in degrees)
        :param mod: (opt, bool) flag to set sinusoidal modulation
        :param mod_freq: (opt, np.float32) modulation frequency (linear, without 2*pi)
        :param mod_ph: (opt, np.float32) modulation phase (in degrees)
        :param iq: (opt, bool) flag to set IQ mixing
        :param iq_params: (opt, dict) dict to store IQ mixing params (e.g. phase/amp/offset)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)

        self.amp = amp
        self.freq = freq
        self.ph = ph
        self.mod = mod
        self.mod_freq = mod_freq
        self.mod_ph = mod_ph
        self.is_analog = True
        self.iq = iq
        self.iq_params = iq_params

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = 'Sin(amp={:.2e} freq={:.2e} ph={:.2f}' \
                  ''.format(self.amp, self.freq, self.ph)

        ret_str = ret_str +  f', mod_freq={self.mod_freq:.2e}, ' \
                             f'mod_ph={self.mod_ph:.2f})' if self.mod else ')'
        return ret_str

    def get_value(self, t_ar, mod=None):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :param mod: (bool) whether to apply sinusoidal modulation
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar = np.array(t_ar, dtype=np.float32)
        ret_ar = np.sin(
            2*np.pi*self.freq*t_ar + np.pi*self.ph/180
        ) * self.amp

        # Use own value of mod parameter if not provided
        if mod is None:
            mod = self.mod

        # Add sin modulation
        if mod:
            ret_ar *= np.sin(2*np.pi*t_ar*self.mod_freq + np.pi*self.mod_ph/180)

        return ret_ar

class PGaussian(PulseBase):
    """ Pulse: Gaussian pulse with optional Sin modulation
    """

    def __init__(self, ch, dur, t0=0, amp=0, stdev=1, 
                mod=False, mod_freq=0, mod_ph=0, 
                iq=False, iq_params=None):
        """ Construct Gaussian Pulse object

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param amp: (opt, np.float32) amplitude (zero-to-peak)
        :param stdev: (opt, np.float32) standard deviation of the gaussian
        :param mod: (opt, bool) flag to set sinusoidal modulation
        :param mod_freq: (opt, np.float32) modulation frequency (linear, without 2*pi)
        :param mod_ph: (opt, np.float32) modulation phase (in degrees)
        :param iq: (opt, bool) flag to set IQ mixing
        :param iq_params: (opt, dict) dict to store IQ mixing params (e.g. phase/amp/offset)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)

        self.amp = amp
        self.stdev = stdev
        self.mod = mod
        self.mod_freq = mod_freq
        self.mod_ph = mod_ph
        self.is_analog = True
        self.iq = iq
        self.iq_params = iq_params

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = f'Gaussian(amp={self.amp:.2e}, ' \
                  f'stdev={self.stdev:.2f}, mod={self.mod}'

        ret_str = ret_str +  f', mod_freq={self.mod_freq:.2e}, ' \
                             f'mod_ph={self.mod_ph:.2f})' if self.mod else ')'

        return ret_str

    def get_value(self, t_ar, mod=None):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :param mod: (bool) whether to apply sinusoidal modulation
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar = np.array(t_ar, dtype=np.float32)

        # Gaussian modulation about the pulse center
        t_mid = self.t0 + self.dur / 2
        ret_ar = np.exp(-0.5 * ((t_ar - t_mid) / self.stdev) ** 2) * self.amp

        # Use own value of mod parameter if not provided
        if mod is None:
            mod = self.mod
        
        # Add sin modulation
        if mod:
            ret_ar *= np.sin(2*np.pi*t_ar*self.mod_freq + np.pi*self.mod_ph/180)

        return ret_ar

class PConst(PulseBase):
    """ Pulse: Constant value with optional Sin modulation
    """

    def __init__(self, ch, dur, t0=0, val=0.0, 
                mod=False, mod_freq=0, mod_ph=0,
                iq=False, iq_params=None):
        """ Construct Constant Pulse

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param val: (opt, np.float32) constant value
        :param mod: (opt, bool) flag to set sinusoidal modulation
        :param mod_freq: (opt, np.float32) modulation frequency (linear, without 2*pi)
        :param mod_ph: (opt, np.float32) modulation phase (in degrees)
        :param iq: (opt, bool) flag to set IQ mixing
        :param iq_params: (opt, dict) dict to store IQ mixing params (e.g. phase/amp/offset)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)
        self.val = val
        self.mod = mod
        self.mod_freq = mod_freq
        self.mod_ph = mod_ph
        self.is_analog = True
        self.iq = iq
        self.iq_params = iq_params

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = f'Const(val={self.val}'

        ret_str =  ret_str + f', mod_freq={self.mod_freq:.2e}, ' \
                             f'mod_ph={self.mod_ph:.2f})' if self.mod else ')'
        
        return ret_str

    def get_value(self, t_ar, mod=None):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :param mod: (bool) whether to apply sinusoidal modulation
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar_len = len(t_ar)
        ret_ar = np.full(t_ar_len, self.val, dtype=np.float32)

        # Use own value of mod parameter if not provided
        if mod is None:
            mod = self.mod

        # Add sin modulation
        if mod:

            ret_ar *= np.sin(2*np.pi*t_ar*self.mod_freq + np.pi*self.mod_ph/180)

        return ret_ar

class PCombined(PulseBase):
    """ Pulse: A meta-pulse comprising of a combination of a list of non-overlapping
        pulses. The value of this pulse is determined by the value of each of the
        constituent pulses.
    """

    def __init__(self, pulselist, dflt):
        """
        :param pulselist: list of pulse objects to be joined together
        """

        if len(pulselist) == 0:
            raise ValueError("Empty list of pulse received.")

        if len(set(pulse.ch for pulse in pulselist)) > 1:
            raise ValueError("More than 1 channel detected. "
                        "All pulses to be merged must have the same channel.")

        # Sort by start times of each pulse 
        pulselist.sort(key=lambda pulse: pulse.t0)

        # Check that pulses are non-overlapping
        for i in range(1, len(pulselist)):
            if pulselist[i].t0 < (pulselist[i-1].t0 + pulselist[i-1].dur):
                raise ValueError("Overlapping pulses detected.")

        ch = pulselist[0].ch
        t0 = pulselist[0].t0
        dur = pulselist[-1].t0 + pulselist[-1].dur - t0

        super().__init__(ch=ch, dur=dur, t0=t0)

        self.pulselist = pulselist
        self.is_analog = True

        if len(set(pulse.mod for pulse in pulselist)) > 1:
            raise ValueError("More than 1 setting for modulation detected. Following the first pulse.")
        if len(set(pulse.mod_freq for pulse in pulselist)) > 1:
            raise ValueError("More than 1 setting for modulation frequency detected. Following the first pulse.")
        if len(set(pulse.mod_ph for pulse in pulselist)) > 1:
            raise ValueError("More than 1 setting for modulation phase detected. Following the first pulse.")

        # Assume that the first item in the list represents the entire combined pulse
        self.mod = pulselist[0].mod
        self.mod_freq = pulselist[0].mod_freq
        self.mod_ph = pulselist[0].mod_ph
        self.iq = pulselist[0].iq

        # Define an automatic default.
        self.auto_default = dflt

    def __str__(self):
        ret_str = "PCombined(" + "\n".join(str(pulse) for pulse in self.pulselist) + ")"

        return ret_str

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """ 

        ret_ar = np.zeros_like(t_ar)

        curr_pulse_idx = 0
        curr_pulse = self.pulselist[curr_pulse_idx]

        # TODO: Improve on this method to avoid getting value for each individual timestep, but 
        # TODO: instead process it in ranges based on each pulse's start and end times.
        # Get the value from each constituent pulse depending on the time value
        for idx, t in enumerate(t_ar):
            while True:
                # We have exhausted all our pulses, just always output default.
                if curr_pulse_idx == len(self.pulselist):
                    value = self.auto_default.get_value([t])
                    break
                elif t < curr_pulse.t0:
                    value = self.auto_default.get_value([t])
                    break
                elif curr_pulse.t0 <= t < (curr_pulse.t0 + curr_pulse.dur):
                    # Temporarily overwrite the constituent pulses' modaulation state
                    value = curr_pulse.get_value([t], self.mod)
                    break
                #t >= (curr_pulse.t0 + curr_pulse.dur)
                else: 
                    # We have finished the current pulse, go to the next one
                    # Now go up the loop to check the value from this new block
                    curr_pulse_idx += 1
                    curr_pulse = self.pulselist[curr_pulse_idx]
                
            ret_ar[idx] = value        

        return ret_ar

    def merge(self, other):
        """ Merge with a PCombined pulse or a normal pulse and returns a new object. 

        The pulselists of both objects are combined and pulse parameters are 
        recomputed by the __init__ function.
        """

        # We follow the default pulse of the self object 
        if type(other) == PCombined:
            return PCombined(self.pulselist + other.pulselist, self.auto_default)
        else:
            return PCombined(self.pulselist + [other], self.auto_default)

# Default Pulse classes -------------------------------------------------------

class DFalse(DfltPulseBase):
    """ DfltPulse: Boolean False
    """

    def __eq__(self, other):
        if not isinstance(other, DFalse):
            return NotImplemented

        return True

    def __str__(self):
        return 'False'

    @staticmethod
    def get_value(t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=bool)) array of samples
        """

        t_ar_len = len(t_ar)
        return np.full(t_ar_len, False)


class DTrue(DfltPulseBase):
    """ DfltPulse: Boolea True
    """

    def __eq__(self, other):
        if not isinstance(other, DTrue):
            return NotImplemented

        return True

    def __str__(self):
        return 'True'

    @staticmethod
    def get_value(t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=bool)) array of samples
        """

        t_ar_len = len(t_ar)
        return np.full(t_ar_len, True)


class DConst(DfltPulseBase):
    """ DfltPulse: Float Constant
    """

    def __init__(self, val=0.0):
        """ Construct Constant DfltPulse object

        :param val: (numpy.float32) value of the constant
        """

        self.val = val

    def __eq__(self, other):
        if not isinstance(other, DConst):
            return NotImplemented

        if self.val == other.val:
            return True
        else:
            return False

    def __str__(self):
        return 'Const(val={})'.format(self.val)

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar_len = len(t_ar)
        ret_ar = np.full(t_ar_len, self.val, dtype=np.float32)

        return ret_ar
