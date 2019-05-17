import numpy as np
from utils.helper_methods import str_to_float, pwr_to_float


class PulseBase:
    def __init__(self):
        # Local or global time is expected
        # as argument of get_value()
        self.local_t = False
        # Pulse duration
        self.dur = 0
        # Type of get_value() return [float or bool]
        self.ret_type = float
        # Expected type of time input for get_value()
        # [numpy array of float or of int]
        self.arg_type = [float]

    def get_value(self, t_ar):
        raise NotImplementedError(
            'Each Pulse class must implement this method'
        )


class High(PulseBase):

    def __init__(self, dur):
        super().__init__()
        self.ret_type = bool
        self.arg_type = [float, int]

        self.dur = str_to_float(dur)

    def get_value(self, t_ar):
        return np.full(len(t_ar), True)

    def __str__(self):
        return 'High(dur={:.2e})'.format(self.dur)


class Sin(PulseBase):

    def __init__(self, dur, amp=0, freq=0, ph=0):
        super().__init__()
        self.ret_type = float
        self.arg_type = [float]
        self.local_t = False

        self.dur = str_to_float(dur)
        self._amp = pwr_to_float(amp)
        self._freq = str_to_float(freq)
        self._ph = ph

    def get_value(self, t_ar):
        t_ar = np.array(t_ar, dtype=np.float)
        return self._amp * np.sin(2*np.pi*self._freq*t_ar + np.pi*self._ph/180)

    def __str__(self):
        ret_str = 'Sin(dur={:.2e} amp={:.2e}, freq={:.2e}, ph={:.2f})' \
                  ''.format(self.dur, self._amp, self._freq, self._ph)
        return ret_str



