import numpy as np
# from utils.helper_methods import str_to_float, pwr_to_float


class PulseBase:
    def __init__(self, ch, dur, t0=0):

        self.ch = ch
        self.t0 = t0
        self.dur = dur


class High(PulseBase):

    def __init__(self, ch, dur, t0=0):
        super().__init__(ch=ch, dur=dur, t0=t0)

    def __str__(self):
        # return 'High(t0={:.2e} dur={:.2e})'.format(self.t0, self.dur)
        return 'High'

    def get_value(self, t_ar):
        return np.full(len(t_ar), True)


class Sin(PulseBase):

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





