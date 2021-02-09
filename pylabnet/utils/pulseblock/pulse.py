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

    def __init__(self, ch, dur, t0=0, amp=0, freq=0, ph=0):
        """ Construct Sin Pulse object

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param amp: (opt, np.float32) amplitude (zero-to-peak)
        :param freq: (opt, np.float32) frequency (linear, without 2*pi)
        :param ph: (opt, np.float32) phase (in degrees)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)

        self._amp = amp
        self._freq = freq
        self._ph = ph
        self.is_analog = True

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = 'Sin(amp={:.2e} freq={:.2e} ph={:.2f})' \
                  ''.format(self._amp, self._freq, self._ph)
        return ret_str

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar = np.array(t_ar, dtype=np.float32)
        ret_ar = self._amp * np.sin(
            2*np.pi*self._freq*t_ar + np.pi*self._ph/180
        )
        return ret_ar

class PGaussian(PulseBase):
    """ Pulse: Guassian pulse with optional Sin modulation
    """

    def __init__(self, ch, dur, t0=0, amp=0, stdev=1, mod=False, mod_freq=0, mod_ph=0):
        """ Construct Gaussian Pulse object

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param amp: (opt, np.float32) amplitude (zero-to-peak)
        :param stdev: (opt, np.float32) standard deviation of the gaussian
        :param mod: (opt, bool) flag to set sinusoidal modulation
        :param mod_freq: (opt, np.float32) modulation frequency (linear, without 2*pi)
        :param mod_ph: (opt, np.float32) modulation phase (in degrees)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)

        self._amp = amp
        self._stdev = stdev
        self._mod = mod
        self._mod_freq = mod_freq
        self._mod_ph = mod_ph
        self.is_analog = True

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = f'SinGaussian(amp={self._amp:.2e}, ' \
                  f'stdev={self._stdev:.2f}, mod={self._mod}'

        ret_str = ret_str +  f', mod_freq={self._mod_freq:.2e}, ' \
                             f'mod_ph={self._mod_ph:.2f})' if self._mod else ')'

        return ret_str

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar = np.array(t_ar, dtype=np.float32)

        # Gaussian modulation about the pulse center
        t_mid = self.t0 + self.dur / 2
        ret_ar = self._amp * np.exp(-0.5 * ((t_ar - t_mid) / self._stdev) ** 2)
        
        # Add sin modulation
        if self._mod:
            ret_ar *= np.sin(2*np.pi*self._mod_freq*t_ar + np.pi*self._mod_ph/180)

        return ret_ar

class PConst(PulseBase):
    """ Pulse: Constant value with optional Sin modulation
    """

    def __init__(self, ch, dur, t0=0, val=0.0, mod=False, mod_freq=0, mod_ph=0):
        """ Construct Constant Pulse

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param val: (opt, np.float32) constant value
        :param mod: (opt, bool) flag to set sinusoidal modulation
        :param mod_freq: (opt, np.float32) modulation frequency (linear, without 2*pi)
        :param mod_ph: (opt, np.float32) modulation phase (in degrees)
        """

        super().__init__(ch=ch, dur=dur, t0=t0)
        self._val = val
        self._mod = mod
        self._mod_freq = mod_freq
        self._mod_ph = mod_ph
        self.is_analog = True

        # Define an automatic default.
        self.auto_default = DConst(val=0.0)

    def __str__(self):
        ret_str = f'Const(val={self._val}'

        ret_str =  ret_str + f', mod_freq={self._mod_freq:.2e}, ' \
                             f'mod_ph={self._mod_ph:.2f})' if self._mod else ')'
        
        return ret_str

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar_len = len(t_ar)
        ret_ar = np.full(t_ar_len, self._val, dtype=np.float32)

        # Add sin modulation
        if self._mod:
            ret_ar *= np.sin(2*np.pi*self._mod_freq*t_ar + np.pi*self._mod_ph/180)

        return ret_ar


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

        self._val = val

    def __eq__(self, other):
        if not isinstance(other, DConst):
            return NotImplemented

        if self._val == other._val:
            return True
        else:
            return False

    def __str__(self):
        return 'Const(val={})'.format(self._val)

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=np.float32)) array of samples
        """

        t_ar_len = len(t_ar)
        ret_ar = np.full(t_ar_len, self._val, dtype=np.float32)

        return ret_ar
