# -*- coding: utf-8 -*-

"""This file contains the pylabnet client which allows qudi to access
Swabian Instruments TT through pylabnet network as SlowCounter.

Steps:
- instantiate Time Tagger
- instantiate pylabnet-SlowCtrWrap (pass ref to Time Tagger as tagger)
- instantiate pylabnet-SlowCtrService and assign module to the created wrapper
- start pylabnet-server for SlowCtrService
- in qudi, instantiate SlowCtrClient as one of the hardware modules

Currently broken, as the link from pylabnet to Qudi has been severed
"""

# from network.core.module import Base, ConfigOption
# from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode
# import rpyc
# import pickle


# class SlowCtrClient(Base, SlowCounterInterface):

#     _modclass = 'SlowCounterClient'
#     _modtype = 'hardware'

#     _cfg_host = ConfigOption(name='host', missing='error')
#     _cfg_port = ConfigOption(name='port', missing='error')

#     def __init__(self, config, **kwargs):
#         super().__init__(config=config, **kwargs)

#         self._host = self._cfg_host
#         self._port = self._cfg_port

#         # References to TT.Counter measurement
#         self._connection = None
#         self._service = None

#     def on_activate(self):

#         self._connection = rpyc.connect(
#             host=self._host,
#             port=self._port,
#             config={'allow_public_attrs': True}
#         )

#         self._service = self._connection.root
#         self.log.info('on_activate(): connected to SlowCounterService: host={} port={}'
#                       ''.format(self._host, self._port))

#     def on_deactivate(self):
#         self._connection.close()
#         self.log.info('on_deactivate(): closed connection to SlowCounterService: host={} port={}'
#                       ''.format(self._host, self._port))

#     def set_up_clock(self, clock_frequency=None, clock_channel=None):
#         """
#         Sets sample clock frequency for the Counter measurement.


#         :param clock_frequency: (float) sample clock frequency. If not given,
#                                 configuration value is used
#         :param clock_channel: ignored (internal timebase is used to generate
#                               sample clock signal)

#         :return: (int) operation status code: 0 - OK
#                                              -1 - Error
#         """

#         return self._service.exposed_set_up_clock(
#             clock_frequency=clock_frequency,
#             clock_channel=clock_channel
#         )

#     def set_up_counter(self,
#                        counter_channels=None,
#                        sources=None,
#                        clock_channel=None,
#                        counter_buffer=None):
#         """
#         Configures the actual counter with a given clock.


#          (list of int) [optional] list of channels
#                      to count clicks on. If not given, config value is used.

#         :param counter_buffer: (int) [optional] size of the memory buffer.
#                                If not given, config value is used.

#         :param counter_channels: ignored
#             This argument should not be used. Counter GUI initializes set of plot curves
#             self.curves during its on_activate() method. It basically calls
#             counter_hardware.get_counter_channels() and uses this list to init self.curves
#             Only after that user can click "Start" button, which will call set_up_counter().
#             And since GUI already has inited set of curves, set of channels must not be
#             modified here! It will case GUI to fail.

#         :param sources: ignored
#         :param clock_channel: ignored

#         :return: (int) operation status code: 0 - OK
#                                              -1 - Error
#         """

#         return self._service.exposed_set_up_counter(
#             counter_channels=counter_channels,
#             sources=sources,
#             clock_channel=clock_channel,
#             counter_buffer=counter_buffer
#         )

#     def close_clock(self):
#         """
#         Closes the clock.

#         :return: (int) error code: 0 - OK
#                                   -1 - Error
#         """

#         return self._service.exposed_close_clock()

#     def close_counter(self):
#         """
#         Closes the counter and cleans up afterwards.

#         :return: (int) error code: 0 - OK
#                                   -1 - Error
#         """

#         return self._service.exposed_close_counter()

#     def get_counter(self, samples=1):
#         """
#         Returns the current counts per second of the counter.

#         :param samples: (int) [optional] number of samples to read in one go
#                         (default is one sample)

#         :return: numpy.array((samples, uint32), dtype=np.uint32)
#         array of count rate [counts/second] arrays of length samples for each click channel
#         Empty array [] is returned in the case of error.
#         """

#         res_pickle = self._service.exposed_get_counter(samples=samples)
#         return pickle.loads(res_pickle)

#     def get_constraints(self):
#         """
#         Retrieve the hardware constrains from the counter device.

#         :return: (SlowCounterConstraints) object with constraints for the counter
#         """

#         constraints = SlowCounterConstraints()
#         # TODO: check values
#         constraints.min_count_frequency = 1
#         constraints.max_count_frequency = 10e9
#         constraints.max_detectors = 8
#         constraints.counting_mode = [CountingMode.CONTINUOUS]

#         return constraints

#     def get_counter_channels(self):
#         """
#         Returns the list of click channel numbers.

#         :return: (list of int) list of click channel numbers
#         """

#         res_pickle = self._service.exposed_get_counter_channels()
#         return pickle.loads(res_pickle)
