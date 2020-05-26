# Historical test module
#
# import rpyc
# import numpy as np
# import pickle
# from pylabnet.utils.logging.logger import LogClient


# class RNG:
#     def __init__(self, mean=0, amp=1, log_host=None, log_port=None, log_tag='RNG', log_level='INFO'):
#         self._mean = mean
#         self._amp = amp

#         self.test_array = np.zeros(1)
#         self.test_array_dict = dict()

#         self.log = LogClient(
#             host=log_host,
#             port=log_port,
#             module_tag=log_tag,
#             level_str=log_level
#         )

#         self.log.info('Started RNG: mean={0}, amp={1}'.format(self._mean, self._amp))

#     def get_params(self):
#         param_dict = dict(mean=self._mean, amp=self._amp)
#         return param_dict

#     def set_params(self, mean=None, amp=None):
#         self.log.info('set_params(mean={}, amp={}) called'.format(mean, amp))

#         if mean is not None:
#             self._mean = mean

#         if amp is not None:
#             self._amp = amp

#         return 0

#     def get_value(self, size=None):
#         values = self._mean + self._amp*(np.random.random(size=size) - 0.5)
#         return values

#     # Timing test
#     def generate_test_array(self, size):
#         self.test_array = np.random.random(size=size)
#         self.log.info(
#             'Successfully generated test_array with size={}'.format(size)
#         )

#     def get_test_array(self):
#         return self.test_array

#     # def get_test_array_pickle(self):
#     #     return pickle.dumps(self.test_array)
#     #
#     # def get_test_array_tostring(self):
#     #     return self.test_array.tostring()

#     # Many active clients test
#     def build_test_array(self, client_number, size=1000):
#         test_ar = client_number + (np.random.random(size=size) - 0.5)
#         self.test_array_dict[str(client_number)] = test_ar

#         self.log.info(
#             'Successfully built test_array. \n'
#             'client_number={}, size={}'.format(client_number, size)
#         )

#         return 0

#     def ret_test_array(self, client_number):
#         return self.test_array_dict[str(client_number)]

#     # Multi-level traceback/stability test
#     def divide(self, a, b):
#         try:
#             c = a / b
#             return c
#         except Exception as exc_obj:
#             self.log.exception('divide(a={}, b={})'.format(a, b))
#             raise exc_obj


# class RNGService(rpyc.Service):

#     _module = None
#     log = None

#     def on_connect(self, conn):
#         # code that runs when a connection is created
#         # (to init the service, if needed)
#         self.log.info('Client connected')

#     def on_disconnect(self, conn):
#         # code that runs after the connection has already closed
#         # (to finalize the service, if needed)
#         self.log.info('Client disconnected')

#     def assign_module(self, module):
#         self._module = module
#         self.log = module.log

#     # ---- Interface --------

#     def exposed_get_params(self):
#         res_dict = self._module.get_params()
#         return pickle.dumps(res_dict)

#     def exposed_set_params(self, mean=None, amp=None):
#         return self._module.set_params(mean=mean, amp=amp)

#     def exposed_get_value(self, size=None):
#         res_ar = self._module.get_value(size=size)
#         return pickle.dumps(res_ar)

#     # Timing test
#     def exposed_generate_test_array(self, size):
#         return self._module.generate_test_array(size=size)

#     def exposed_get_test_array(self):
#         return pickle.dumps(self._module.test_array)

#     # Many active clients test
#     def exposed_build_test_array(self, client_number, size=1000):
#         return self._module.build_test_array(
#             client_number=client_number,
#             size=size
#         )

#     def exposed_ret_test_array(self, client_number):
#         res = self._module.ret_test_array(client_number=client_number)
#         return pickle.dumps(res)

#     # Multi-level traceback/stability test
#     def exposed_divide(self, a, b):
#         return self._module.divide(a=a, b=b)


# class RNGClient:
#     def __init__(self, host, port):

#         # Internal vars to store server info
#         self._host = ''
#         self._port = 0

#         # Internal vars to store refs to server
#         self._connection = None
#         self._service = None

#         # Connect to server
#         self.connect(host=host, port=port)

#     def connect(self, host='place_holder', port=-1):

#         # Update server address if new values are given
#         if host != 'place_holder':
#             self._host = host
#         if port != -1:
#             self._port = port

#         # Clean-up old connection if it exists
#         if self._connection is not None or self._service is not None:
#             try:
#                 self._connection.close()
#             except:
#                 pass

#             self._connection = None
#             self._service = None

#         # Connect to server
#         try:
#             self._connection = rpyc.connect(
#                 host=self._host,
#                 port=self._port,
#                 config={'allow_public_attrs': True}
#             )
#             self._service = self._connection.root

#             return 0

#         except Exception as exc_obj:
#             self._connection = None
#             self._service = None
#             raise exc_obj

#     # Interface methods

#     def get_params(self):
#         res_pickle = self._service.exposed_get_params()
#         return pickle.loads(res_pickle)

#     def set_params(self, mean=None, amp=None):
#         ret_code = self._service.exposed_set_params(
#             mean=mean,
#             amp=amp
#         )
#         return ret_code

#     def get_value(self, size=None):
#         pickled_ret_ar = self._service.exposed_get_value(size=size)
#         return pickle.loads(pickled_ret_ar)

#     # Timing test
#     def generate_test_array(self, size):
#         return self._service.exposed_generate_test_array(
#             size=size
#         )

#     def get_test_array(self):
#         pickled_ret_ar = self._service.exposed_get_test_array()
#         return pickle.loads(pickled_ret_ar)

#     # Many active clients test
#     def build_test_array(self, client_number, size=1000):
#         return self._service.exposed_build_test_array(
#             client_number=client_number,
#             size=size
#         )

#     def ret_test_array(self, client_number):
#         res_pickle = self._service.exposed_ret_test_array(
#             client_number=client_number
#         )
#         return pickle.loads(res_pickle)

#     # Multi-level traceback/stability test
#     def divide(self, a, b):
#         return self._service.exposed_divide(
#             a=a,
#             b=b
#         )
