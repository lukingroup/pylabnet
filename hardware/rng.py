import rpyc
import numpy as np
import pickle


class RNG:
    def __init__(self):
        self._mean = 0
        self._amp = 0

        self.test_array = np.zeros(1)
        self.test_array_dict = dict()

    def get_params(self):
        param_dict = dict(mean=self._mean, amp=self._amp)
        return param_dict

    def set_params(self, mean=None, amp=None):
        if mean is not None:
            self._mean = mean

        if amp is not None:
            self._amp = amp

        return 0

    def get_value(self, size=None):
        values = self._mean + self._amp*(np.random.random(size=size) - 0.5)
        return values

    # Timing test
    def generate_test_array(self, size):
        self.test_array = np.random.random(size=size)

    def get_test_array(self):
        return self.test_array

    # def get_test_array_pickle(self):
    #     return pickle.dumps(self.test_array)
    #
    # def get_test_array_tostring(self):
    #     return self.test_array.tostring()

    # Many active clients test
    def build_test_array(self, client_number, size=1000):
        test_ar = client_number + (np.random.random(size=size) - 0.5)
        self.test_array_dict[str(client_number)] = test_ar
        return 0

    def ret_test_array(self, client_number):
        return self.test_array_dict[str(client_number)]


class RNGService(rpyc.Service):

    _module = None

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def assign_module(self, module):
        self._module = module

    # ---- Interface --------

    def exposed_get_params(self):
        res_dict = self._module.get_params()
        return pickle.dumps(res_dict)

    def exposed_set_params(self, mean=None, amp=None):
        return self._module.set_params(mean=mean, amp=amp)

    def exposed_get_value(self, size=None):
        res_ar = self._module.get_value(size=size)
        return pickle.dumps(res_ar)

    # Timing test
    def exposed_generate_test_array(self, size):
        return self._module.generate_test_array(size=size)

    def exposed_get_test_array(self):
        return pickle.dumps(self._module.test_array)

    # Many active clients test
    def exposed_build_test_array(self, client_number, size=1000):
        return self._module.build_test_array(
            client_number=client_number,
            size=size
        )

    def exposed_ret_test_array(self, client_number):
        res = self._module.ret_test_array(client_number=client_number)
        return pickle.dumps(res)


class RNGClient:
    def __init__(self, port, host='localhost'):

        self._host = host
        self._port = port

        self._connection = None
        self._service = None

        self.connect()

    def connect(self):
        if self._connection is not None or self._service is not None:
            try:
                self._connection.close()
            except:
                pass

            del self._service, self._connection

        try:
            self._connection = rpyc.connect(
                host=self._host,
                port=self._port,
                config={'allow_public_attrs': True}
            )
            self._service = self._connection.root
            return 0

        except:
            print('[ERROR] connect(): failed to establish connection')
            return -1

    def get_params(self):
        try:
            res_pickle = self._service.exposed_get_params()
            return pickle.loads(res_pickle)

        except EOFError:
            print('[ERROR] get_params(): connection lost')
            return dict()

    def set_params(self, mean=None, amp=None):
        try:
            ret_code = self._service.exposed_set_params(
                mean=mean,
                amp=amp
            )
            return ret_code

        except EOFError:
            print('[ERROR] set_params(): connection lost')
            return -1

    def get_value(self, size=None):
        try:
            pickled_ret_ar = self._service.exposed_get_value(size=size)
            return pickle.loads(pickled_ret_ar)

        except EOFError:
            print('[ERROR] get_value(): connection lost')
            return []

    # Timing test
    def generate_test_array(self, size):
        return self._service.exposed_generate_test_array(size=size)

    def get_test_array(self):
        pickled_ret_ar = self._service.exposed_get_test_array()
        return pickle.loads(pickled_ret_ar)

    # Many active clients test
    def build_test_array(self, client_number, size=1000):
        return self._service.exposed_build_test_array(
            client_number=client_number,
            size=size
        )

    def ret_test_array(self, client_number):
        try:
            res_pickle = self._service.exposed_ret_test_array(client_number=client_number)
            return pickle.loads(res_pickle)

        # TimeoutError
        except EOFError:
            print('[ERROR] get_params(): connection lost')
            return dict()
