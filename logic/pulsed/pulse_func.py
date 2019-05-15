import numpy as np


class PulseFuncBase:

    def get_value(self, t_list):
        raise NotImplementedError(
            'This method should be implemented by every PulseFunc class'
        )


class Dflt(PulseFuncBase):

    def get_value(self, t_list):
        return np.zeros(shape=len(t_list))


class High(PulseFuncBase):

    def get_value(self, t_list):
        return np.ones(shape=len(t_list))


class Sin(PulseFuncBase):

    def __init__(self, amp=0, freq=0, phase=0):
        self._amp = amp
        self._freq = freq
        self._phase = phase

    def get_value(self, t_list):
        value_ar = self._amp * np.sin(self._freq*t_list + self._phase)
        return value_ar
