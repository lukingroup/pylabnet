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

class PTrue(PulseBase):
    """ Pulse: Boolean True
    """

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

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

    def __str__(self):
        return 'False'

    def get_value(self, t_ar):
        """ Returns array of samples

        :param t_ar: (numpy.array) array of time points
        :return: (numpy.array(dtype=bool)) array of samples
        """

        return np.full(len(t_ar), False)


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


class PConst(PulseBase):
    """ Pulse: Constant
    """

    def __init__(self, ch, dur, t0=0, val=0.0):
        """ Construct Constant Pulse

        :param ch: (str) channel name
        :param dur: (numeric) duration of the pulse
        :param t0: (opt, numeric) position of the pulse beginning
        :param val: (opt, np.float32) constant value
        """

        super().__init__(ch=ch, dur=dur, t0=t0)
        self._val = val

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



