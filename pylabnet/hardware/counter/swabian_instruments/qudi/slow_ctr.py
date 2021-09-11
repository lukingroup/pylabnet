""" pylabnet measurement and service classes for Swabian Instruments TimeTagger
which implements qudi's SlowCounter interface.

This file contains pylabnet wrapper and service classes to allow qudi to
access Swabian Instruments TT through pylabnet network as SlowCounter.

Steps:
- instantiate TimeTagger
- instantiate pylabnet-SlowCtrWrap (pass ref to TimeTagger as tagger)
- instantiate pylabnet-SlowCtrService and assign module to the created wrapper
- start pylabnet-server for SlowCtrService
- in qudi, instantiate SlowCtrClient as one of the hardware modules
"""

from pylabnet.network.core.service_base import ServiceBase
import TimeTagger as TT
import time
import copy
import pickle


class Wrap:
    """ Measurement instance which implements qudi's SlowCounter interface.
    """

    def __init__(self, tagger, channel_list, clock_frequency, buffer_size):

        # References to the device and to TT.Counter measurement
        self._tagger = tagger
        self._counter = None

        # Counter parameters
        self._channel_list = channel_list
        self._clock_frequency = clock_frequency
        self._buffer_size = buffer_size

        self._bin_width = 0
        self._bin_width_sec = 0

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """
        Sets sample clock frequency for the Counter measurement.


        :param clock_frequency: (float) sample clock frequency. If not given,
                                configuration value is used
        :param clock_channel: ignored (internal timebase is used to generate
                              sample clock signal)

        :return: (int) operation status code: 0 - OK
                                             -1 - Error
        """

        # Use config value, if no clock_frequency is specified
        if clock_frequency is None:
            clock_frequency = self._clock_frequency

        # Calculate final bin width
        bin_width = int(1e12 / clock_frequency)  # in picoseconds, for device
        bin_width_sec = bin_width * 1e-12      # is seconds, for software timing

        # Set new values param to internal variables
        self._bin_width = bin_width
        self._bin_width_sec = bin_width_sec

        return 0

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """
        Configures the actual counter with a given clock.


         (list of int) [optional] list of channels
                     to count clicks on. If not given, config value is used.

        :param counter_buffer: (int) [optional] size of the memory buffer.
                               If not given, config value is used.

        :param counter_channels: ignored
            This argument should not be used. Counter GUI initializes set of plot curves
            self.curves during its on_activate() method. It basically calls
            counter_hardware.get_counter_channels() and uses this list to init self.curves
            Only after that user can click "Start" button, which will call set_up_counter().
            And since GUI already has inited set of curves, set of channels must not be
            modified here! It will case GUI to fail.

        :param sources: ignored
        :param clock_channel: ignored

        :return: (int) operation status code: 0 - OK
                                             -1 - Error
        """

        # Set counter channels
        if counter_channels is not None:
            channel_list = counter_channels
        else:
            channel_list = self._channel_list
        # apply counter channel change
        self.set_counter_channels(channel_list=channel_list)

        # Set buffer size
        if counter_buffer is not None:
            buffer_size = counter_buffer
        else:
            buffer_size = self._buffer_size
        # sanity check:
        if not isinstance(buffer_size, int) or buffer_size <= 0:
            # self.log.error('set_up_counter(): invalid parameter value counter_buffer = {}.'
            #                'This parameter must be a positive integer.'
            #                ''.format(buffer_size))
            return -1
        # apply buffer size change
        self._buffer_size = buffer_size

        # Create instance of Counter measurement
        try:
            self._counter = TT.Counter(
                tagger=self._tagger,
                channels=self._channel_list,
                binwidth=self._bin_width,
                n_values=self._buffer_size
            )
        # handle initialization error (TT functions always produce NotImplementedError)
        except NotImplementedError:
            self._counter = None
            # self.log.error('set_up_counter(): failed to instantiate TT.Counter measurement')
            return -1

        # Start Counter
        # (TT.Counter measurement starts running immediately after instantiation,
        # so it is necessary to erase all counts collected since instantiation)
        self._counter.stop()
        self._counter.clear()
        self._counter.start()

        return 0

    def close_clock(self):
        """
        Closes the clock.

        :return: (int) error code: 0 - OK
                                  -1 - Error
        """

        # self._bin_width = 0
        # self._bin_width_sec = 0

        return 0

    def close_counter(self):
        """
        Closes the counter and cleans up afterwards.

        :return: (int) error code: 0 - OK
                                  -1 - Error
        """

        # Try stopping and clearing TT.Counter measurement
        try:
            self._counter.stop()
            self._counter.clear()
        # Handle the case of exception in TT function call (NotImplementedError)
        # and the case of self._ctr = None (AttributeError)
        except (NotImplementedError, AttributeError):
            pass

        # Remove reference to the counter
        # self._ctr = None

        # Clear counter parameters
        # self._buffer_size = []

        # Do not clear channel list:
        # Counter GUI inits its list of curves self.curves
        # by calling counter_hardware.get_counter_channels() before
        # calling counter_hardware.set_up_counter()
        # If one clears _channel_list here, GUI will fail at the next
        # "Start" button click after reloading.
        #
        # self._channel_list = []

        return 0

    def get_counter(self, samples=1):
        """
        Returns the current counts per second of the counter.

        :param samples: (int) [optional] number of samples to read in one go
                        (default is one sample)

        :return: numpy.array((samples, uint32), dtype=np.uint32)
        array of count rate [counts/second] arrays of length samples for each click channel
        Empty array [] is returned in the case of error.
        """

        # Sanity check: samples has valid value
        if samples != 1:
            if not isinstance(samples, int) or samples <= 0:
                # self.log.error('get_counter(): invalid argument samples={0}. This argument must be a positive integer'
                #                ''.format(samples))
                return []

        # MORE SOPHISTICATED VERSION
        # (WORKS TOO SLOWLY: PROBABLY BECAUSE OF SLOW INTEGER DIVISION OF LARGE INTEGERS)
        #
        # start_time = time.time()
        # while time.time() - start_time < self._timeout:
        #     new_complete_bins = self._ctr.getCaptureDuration() // self._bin_width - self._last_read_bin
        #
        #     self._overflow = new_complete_bins
        #     # self.log.error('new_complete_bins = {}'.format(new_complete_bins))
        #
        #     if new_complete_bins < samples:
        #         time.sleep(self._bin_width_sec/2)
        #         continue
        #     elif new_complete_bins == samples:
        #         self._last_read_bin += new_complete_bins
        #         break
        #     else:
        #         # self.log.warn('Counter is overflowing. \n'
        #         #               'Software pulls data in too slowly and counter bins are too short, '
        #         #               'such that some bins are lost. \n'
        #         #               'Try reducing sampling rate or increasing oversampling')
        #         self._last_read_bin += new_complete_bins
        #         break

        # Wait for specified number of samples (samples parameter) to be accumulated
        #
        # This approach is very naive and is more or less accurate for
        # clock frequency below 50 Hz.
        #
        # For higher frequencies, the actual time sampling interval is determined
        # by software delays (about 1 ms). Counter measurement overflows
        # (most of the samples are over-written before software reads them in)
        # but does not fail. The only problem here is that time axis on the count-trace
        # graph is no longer accurate:
        # the difference between consecutive tick labels is much smaller than the actual
        # time interval between measured samples (about 1 ms)
        time.sleep(samples * self._bin_width_sec)

        # read-in most recent 'samples' samples
        try:
            count_array = self._counter.getData()[:, -samples:]
        except NotImplementedError:
            # self.log.error('get_counter() reading operation failed')
            return []
        except AttributeError:
            # self.log.error('get_counter(): counter was not initialized')
            return []

        # Calculate count rate [count/sec]
        count_rate_array = count_array / self._bin_width_sec

        return count_rate_array

    def get_counter_channels(self):
        """
        Returns the list of click channel numbers.

        :return: (list of int) list of click channel numbers
        """

        return copy.deepcopy(self._channel_list)

    def set_counter_channels(self, channel_list=None):
        """
        Set click channel list.

        Notice that this method only modifies internal variable _channel_list.
        To apply the change to the counter, one has to call set_up_counter() again.


        :param channel_list: (list of int) list of channels to count clicks on

        :return: (list of int) actual list of click channels
        """

        if channel_list is None:
            return self.get_counter_channels()

        # Sanity check:
        all_channels = self._get_all_channels()
        if not set(channel_list).issubset(set(all_channels)):
            # self.log.error('set_counter_channels(): requested list of channels is invalid: '
            #                'some channels are not present on the device.'
            #                'requested list: {0} \n'
            #                'available channels: {1}'
            #                ''.format(channel_list, all_channels))
            return self.get_counter_channels()

        # Apply changes to internal variable self._channel_list
        self._channel_list = channel_list
        # Sort channel numbers, such that channel order does not depend
        # on order of numbers in the config file
        self._channel_list.sort()

        return self.get_counter_channels()

    def _get_all_channels(self):
        """
        Return list of all channels available on the device.

        Positive/negative values correspond to rising/falling edge detection.
        For example:
            1 means 'rising edge on connector 1'
            -1 means 'falling edge on connector 1


        :return: (list of int) list of all available channel numbers,
                               including edge sign.
        """

        try:
            available_channel_tuple = list(
                self._tagger.getChannelList(TT.TT_CHANNEL_RISING_AND_FALLING_EDGES)
            )
        # handle exception in the call (TT functions normally produce NotImplementedError)
        except NotImplementedError:
            # self.log.error('_get_all_channels(): communication with the device failed')
            return []
        # handle the case of self._tagger = None
        except AttributeError:
            # self.log.error('_get_all_channels(): _tagger is None. Initialize device first')
            return []

        return list(available_channel_tuple)


class Service(ServiceBase):

    def exposed_set_up_clock(self, clock_frequency=None, clock_channel=None):
        """
        Sets sample clock frequency for the Counter measurement.


        :param clock_frequency: (float) sample clock frequency. If not given,
                                configuration value is used
        :param clock_channel: ignored (internal timebase is used to generate
                              sample clock signal)

        :return: (int) operation status code: 0 - OK
                                             -1 - Error
        """

        return self._module.set_up_clock(
            clock_frequency=clock_frequency,
            clock_channel=clock_channel
        )

    def exposed_set_up_counter(self, counter_channels=None, sources=None, clock_channel=None, counter_buffer=None):
        """
        Configures the actual counter with a given clock.


         (list of int) [optional] list of channels
                     to count clicks on. If not given, config value is used.

        :param counter_buffer: (int) [optional] size of the memory buffer.
                               If not given, config value is used.

        :param counter_channels: ignored
            This argument should not be used. Counter GUI initializes set of plot curves
            self.curves during its on_activate() method. It basically calls
            counter_hardware.get_counter_channels() and uses this list to init self.curves
            Only after that user can click "Start" button, which will call set_up_counter().
            And since GUI already has inited set of curves, set of channels must not be
            modified here! It will case GUI to fail.

        :param sources: ignored
        :param clock_channel: ignored

        :return: (int) operation status code: 0 - OK
                                             -1 - Error
        """

        return self._module.set_up_counter(
            counter_channels=counter_channels,
            sources=sources,
            clock_channel=clock_channel,
            counter_buffer=counter_buffer
        )

    def exposed_close_clock(self):
        """
        Closes the clock.

        :return: (int) error code: 0 - OK
                                  -1 - Error
        """

        return self._module.close_clock()

    def exposed_close_counter(self):
        """
        Closes the counter and cleans up afterwards.

        :return: (int) error code: 0 - OK
                                  -1 - Error
        """

        return self._module.close_ctr()

    def exposed_get_counter(self, samples=1):
        """
        Returns the current counts per second of the counter.

        :param samples: (int) [optional] number of samples to read in one go
                        (default is one sample)

        :return: numpy.array((samples, uint32), dtype=np.uint32)
        array of count rate [counts/second] arrays of length samples for each click channel
        Empty array [] is returned in the case of error.
        """

        res = self._module.get_counter(samples=samples)
        return pickle.dumps(res)

    def exposed_get_counter_channels(self):
        """
        Returns the list of click channel numbers.

        :return: (list of int) list of click channel numbers
        """

        res = self._module.get_counter_channels()
        return pickle.dumps(res)
