import rpyc
import numpy as np
import pickle


class RNG:
    def __init__(self):
        self._mean = 0
        self._amp = 0

        self.test_array = np.zeros(1)

    def get_params(self):
        param_dict = dict(mean=self._mean, amp=self._amp)
        return param_dict

    def set_params(self, mean=None, amp=None):
        if mean is not None:
            self._mean = mean

        if amp is not None:
            self._amp = amp

    def get_value(self, size=None):
        values = self._mean + self._amp*(np.random.random(size=size) - 0.5)
        return values

    # Timing test

    def generate_test_array(self, size):
        self.test_array = np.random.random(size=size)

    def get_test_array_tuple(self):
        return convert_to_tuple(self.test_array)

    def get_test_array_pickle(self):
        return pickle.dumps(self.test_array)

    def get_test_array_tostring(self):
        return self.test_array.tostring()


def convert_to_tuple(ar):
    try:
        return tuple(convert_to_tuple(i) for i in ar)
    except TypeError:
        return ar


# class RNGService(rpyc.Service):
#
#     _module = None
#
#     def on_connect(self, conn):
#         # code that runs when a connection is created
#         # (to init the service, if needed)
#         pass
#
#     def on_disconnect(self, conn):
#         # code that runs after the connection has already closed
#         # (to finalize the service, if needed)
#         pass
#
#     def assign_module(self, module):
#         self._module = module
#
#     # ---- Interface --------
#
#     def exposed_get_params(self):
#         return self._module.get_params()
#
#     def exposed_set_params(self, mean=None, amp=None):
#         return self._module.set_params(mean=mean, amp=amp)
#
#     def exposed_get_value(self, size=None):
#         return self._module.get_value(size=size)


# class RNGClient:
#     pass
