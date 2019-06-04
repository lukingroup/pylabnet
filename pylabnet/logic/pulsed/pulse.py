import numpy as np
# from utils.helper_methods import str_to_float, pwr_to_float


#
#   Base classes
#


class PulseBase:
    def __init__(self, ch, dur, t0=0):

        self.ch = ch
        self.t0 = t0
        self.dur = dur


class DfltPulseBase:

    def __eq__(self, other):
        raise NotImplementedError(
            'Every default pulse class has to define __eq__() method. \n'
            'Reason: during insert_pb() call a check for conflicts between '
            'default pulse objects on the overlapping channels is performed'
            'by direct comparison operation.'
        )


#
#   Pulse classes
#

class PTrue(PulseBase):

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

    def __str__(self):
        # return 'High(t0={:.2e} dur={:.2e})'.format(self.t0, self.dur)
        return 'True'

    def get_value(self, t_ar):
        return np.full(len(t_ar), True)


class PFalse(PulseBase):

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

    def __str__(self):
        # return 'False(t0={:.2e} dur={:.2e})'.format(self.t0, self.dur)
        return 'False'

    def get_value(self, t_ar):
        return np.full(len(t_ar), False)


class PSin(PulseBase):

    def __init__(self, ch, dur, t0=0, amp=0, freq=0, ph=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

        self._amp = amp
        self._freq = freq
        self._ph = ph

    def __str__(self):
        # ret_str = 'Sin(t0={:.2e} dur={:.2e} | amp={:.2e} freq={:.2e} ph={:.2f})' \
        #           ''.format(self.t0, self.dur, self._amp, self._freq, self._ph)
        ret_str = 'Sin(amp={:.2e} freq={:.2e} ph={:.2f})' \
                  ''.format(self._amp, self._freq, self._ph)
        return ret_str

    def get_value(self, t_ar):
        t_ar = np.array(t_ar, dtype=np.float)
        ret_ar = self._amp * np.sin(
            2*np.pi*self._freq*t_ar + np.pi*self._ph/180
        )
        return ret_ar

#
#   Default Pulse classes
#


class DFalse(DfltPulseBase):

    def __eq__(self, other):
        if not isinstance(other, DFalse):
            return NotImplemented

        return True

    def __str__(self):
        return 'False'

    @staticmethod
    def get_value(t_ar):
        t_ar_len = len(t_ar)
        return np.full(t_ar_len, False)


class DTrue(DfltPulseBase):

    def __eq__(self, other):
        if not isinstance(other, DTrue):
            return NotImplemented

        return True

    def __str__(self):
        return 'True'

    @staticmethod
    def get_value(t_ar):
        t_ar_len = len(t_ar)
        return np.full(t_ar_len, True)


class DConst(DfltPulseBase):

    def __init__(self, val=0):
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
        t_ar_len = len(t_ar)
        ret_ar = np.full(t_ar_len, self._val, dtype=np.float32)

        return ret_ar



