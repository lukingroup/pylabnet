import rpyc
import TimeTagger as TT
import time
import copy
import pickle
import numpy as np


class GatedCounter:

    def __init__(self, tagger, click_channel, gate_channel):
        """Instantiate gated counter

        :param tagger:
        :param click_channel: (int|list of int) clicks on all specified channels
                              will be summed into one logical channel
        :param gate_channel: (int) positive/negative channel number - count while
                             gate is high/low
        """

        # Reference to tagger
        self._tagger = tagger
        # Log device ID information to demonstrate that connection indeed works
        serial = self._tagger.getSerial()
        model = self._tagger.getModel()
        # self.log.info('Got reference to Swabian Instruments TimeTagger device \n'
        #               'Serial number: {0}, Model: {1}'
        #               ''.format(serial, model))
        print('[INFO] Got reference to Swabian Instruments TimeTagger device \n'
              'Serial number: {0}, Model: {1}'.format(serial, model))

        # Gated Counter
        # reference to the TT.CountBetweenMarkers measurement instance
        self._counter = None
        # number of count bins:
        #   length of returned 1D count array, the expected number of gate pulses,
        #   the size of allocated memory buffer.
        # must be given as argument of init_counter() call
        self._bin_number = 0

        # Channel assignments
        self._click_channel = 0
        self._gate_channel = 0
        # reference to Combiner object
        #   (if _click_channel is a list - then counts on all channels are summed
        #   into virtual channel - self._combiner.getChannel())
        self._combiner = None
        # apply channel assignment
        self.set_channel_assignment(
            click_channel=click_channel,
            gate_channel=gate_channel
        )

        # Module status code
        #  -1 "void"
        #   0 "idle"
        #   1 "in_progress"
        #   2 "finished"
        self._status = -1
        self._set_status(-1)

        # Once __init__() call is complete,
        # the counter is ready to be initialized by the above-lying logic though init_counter() call

    # ---------------- Interface ---------------------------

    def init_counter(self, bin_number):
        # Close existing counter, if it was initialized before
        if self.get_status() != -1:
            self.close_counter()

        # Instantiate counter measurement
        try:
            self._counter = TT.CountBetweenMarkers(
                tagger=self._tagger,
                click_channel=self._click_channel,
                begin_channel=self._gate_channel,
                end_channel=-self._gate_channel,
                n_values=bin_number
            )
            # set status to "idle"
            self._set_status(0)

            # save bin_number in internal variable
            self._bin_number = bin_number

        # handle NotImplementedError (typical error, produced by TT functions)
        except NotImplementedError:
            # self.log.error('init_counter(): instantiation of CountBetweenMarkers measurement failed')
            print('[ERROR] init_counter(): instantiation of CountBetweenMarkers measurement failed')

            # remove reference to the counter measurement
            self._counter = None
            # set status to "void"
            self._set_status(-1)

            return -1

        # Prepare counter to be started by start_counting()
        # (CountBetweenMarkers measurement starts running immediately after instantiation,
        # so it is necessary to stop it and erase all counts collected between instantiation and stop() call)
        self._counter.stop()
        self._counter.clear()

        return 0

    def close_counter(self):

        # Try to stop and to clear TT.CountBetweenMarkers measurement instance
        try:
            self._counter.stop()
            self._counter.clear()
        except:
            pass

        # Remove reference, set status to "void"
        self._counter = None
        self._set_status(-1)

        return 0

    def start_counting(self):

        current_status = self.get_status()

        # Sanity check: ensure that counter is not "void"
        if current_status == -1:
            # self.log.error('start_counting(): counter is in "void" state - it ether was not initialized '
            #                'or was closed. Initialize it by calling init_counter()')
            print('[ERROR] start_counting(): counter is in "void" state - it ether was not initialized '
                  'or was closed. Initialize it by calling init_counter()')
            return -1

        # Terminate counting if it is already running
        if current_status == 1:
            self.terminate_counting()

        # Try stopping and restarting counter measurement
        try:
            self._counter.stop()  # does not fail even if the measurement is not running
            self._counter.clear()
            self._counter.start()

            # set status to "in_progress"
            self._set_status(1)
            return 0

        # handle exception in TT function calls [NotImplementedError]
        except NotImplementedError:
            # Since stop() and clear() methods are very robust,
            # this part is only executed if counter is totally broken.
            # In this case it makes sense to close counter.
            self.close_counter()

            # self.log.error('start_counting(): call failed. Counter was closed. \n'
            #                'Re-initialize counter by calling init_counter() again')
            print('[ERROR] start_counting(): call failed. Counter was closed. \n'
                  'Re-initialize counter by calling init_counter() again')
            return -1

    def terminate_counting(self):

        # Action of this method is non-trivial for "in_progress" state only
        if self.get_status() != 1:
            return 0

        # Try stopping and clearing counter measurement
        try:
            # stop counter, clear count array
            self._counter.stop()
            self._counter.clear()

            # set status to "idle"
            self._set_status(0)
            return 0

        # handle exception in TT.stop()/TT.clear()
        except NotImplementedError:
            # Since stop() and clear() methods are very robust,
            # this part is only executed if counter is totally broken.
            # In this case it makes sense to close counter.
            self.close_counter()

            # self.log.error('terminate_counting(): call failed. Counter was closed')
            print('[ERROR] terminate_counting(): call failed. Counter was closed')
            return -1

    def get_status(self):

        # Check that counter measurement was initialized and that the connection works
        # by calling isRunning()
        #  -- if self._counter is None or if connection is broken, call will rise some
        #     exception. In this case "void" status should be set
        #  -- if counter was initialized and connection works, it will return successfully
        #     (True or False, but the result does not matter)
        #     and further choice between "idle", "in_progress", and "finished" should be made
        try:
            self._counter.isRunning()
        except:
            # set status to "void"
            self._status = -1

        # No handling of "idle" and "finished" status is needed:
        # it will be returned by self._status as is

        # Handle "in_progress" status
        #   This status means that measurement was started before.
        #   Now one needs to check if it is already finished or not.
        #   If measurement is complete, change status to "finished".
        if self._status == 1:
            if self._counter.ready():

                self._counter.stop()
                self._status = 2

        return copy.deepcopy(self._status)

    def get_count_array(self, timeout=-1):

        # If current status is "in_progress",
        # wait for transition to some other state:
        #   "finished" if measurement completes successfully,
        #   "idle" if measurement is terminated,
        #   "void" if counter breaks
        start_time = time.time()
        sleep_time = abs(timeout)/100

        while self.get_status() == 1:
            # stop waiting if timeout elapses
            if time.time()-start_time > timeout >= 0:
                break
            time.sleep(sleep_time)

        # Analyze current status and return correspondingly
        status = self.get_status()

        # return data only in the case of "finished" state
        if status == 2:
            count_array = np.array(
                self._counter.getData(),
                dtype=np.uint32
            )
            return count_array

        # return empty list for all other states ("in_progress", "idle", and "void")
        else:
            if status == 1:
                # self.log.warn('get_count_array(): operation timed out, but counter is still running. \n'
                #               'Try calling get_count_array() later or terminate process by terminate_counting().')
                print('[WARN] get_count_array(): operation timed out, but counter is still running. \n'
                      'Try calling get_count_array() later or terminate process by terminate_counting().')
            elif status == 0:
                # self.log.warn('get_count_array(): counter is "idle" - nothing to read')
                print('[WARN] get_count_array(): counter is "idle" - nothing to read')
            else:
                # self.log.error('get_count_array(): counter broke and was deleted')
                print('[ERROR] get_count_array(): counter broke and was deleted')

            return []

    # ------------------------------------------------------

    def _set_status(self, new_status):
        """Method to set new status in a clean way.

        This method compares the requested new_status with current status
        and checks if this transition is possible. If transition is possible,
        the change is applied to self._status. Otherwise, no status change
        is applied, -1 is returned, and error message is logged.


        :param new_status: (int) new status value
                            -1 - "void"
                             0 - "idle"
                             1 - "in_progress"
                             2 - "finished"

        :return: (int) operation status code:
                 0 - OK, change was accepted and applied
                -1 - Error, impossible transition was requested,
                     no state change was applied
        """

        # Transition to "void" is always possible
        # by calling close_counter()
        if new_status == -1:
            self._status = -1
            return 0

        # Transition to "idle" is possible from
        #   "void" by calling init_counter()
        #   "in_progress" by calling terminate_counting()
        if new_status == 0:
            if self._status==-1 or self._status==1:
                self._status = 0
                return 0
            else:
                # self.log.error('_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                #                'Counter status was not changed.'
                #                ''.format(new_status, self._status))
                print('[ERROR] _set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                      'Counter status was not changed.'
                      ''.format(new_status, self._status))
                return -1

        # Transition to "in_progress" is possible from
        #   "idle" by calling start_counting()
        #   "finished" by calling start_counting()
        if new_status == 1:
            if self._status==0 or self._status==2:
                self._status = 1
                return 0
            else:
                # self.log.error('_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                #                'Counter status was not changed.'
                #                ''.format(new_status, self._status))
                print('[ERROR] _set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                      'Counter status was not changed.'
                      ''.format(new_status, self._status))
                return -1

        # Transition to "finished" is only possible from "in_progress"
        # by successful completion of count_array accumulation
        if new_status == 2:
            if self._status == 1:
                self._status = 2
                return 0
            else:
                # self.log.error('_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                #                'Counter status was not changed.'
                #                ''.format(new_status, self._status))
                print('[ERROR] _set_status(): transition to new_status={0} from self._status={1} is impossible. \n'
                      'Counter status was not changed.'
                      ''.format(new_status, self._status))
                return -1

    def get_channel_assignment(self):
        """Returns dictionary containing current channel assignment:
            {
                'click_channel': (int) click_channel_number_including_edge_sign
                'gate_channel': (int) gate_channel_number_including_edge_sign
            }

        :return: dict('click_channel': _, 'gate_channel': _)
        """

        click_channel = copy.deepcopy(self._click_channel)
        gate_channel = copy.deepcopy(self._gate_channel)

        return {'click_channel': click_channel, 'gate_channel': gate_channel}

    def set_channel_assignment(self, click_channel=None, gate_channel=None):
        """Sets click channel and and gate channel.

        This method only changes internal variables
        self._click_channel and self._gate_channel.
        To apply the channel update, call  init_counter() again.


        :param click_channel: (int|list of int) click channel number
                              positive/negative values - rising/falling edge detection
                              if list is given, clicks on all specified channels
                              will be merged into one logic channel

        :param gate_channel: (int) channel number
                             positive/negative - count during high/low gate level

        :return: (dict) actually channel assignment:
                        {
                            'click_channel': (int) click_chnl_num,
                            'gate_channel': (int) gate_chnl_num
                        }
        """

        if click_channel is not None:
            # for convenience bring int type of input to list of int
            if isinstance(click_channel, list):
                click_channel_list = click_channel
            elif isinstance(click_channel, int):
                click_channel_list = [click_channel]
            else:
                # unknown input type
                # self.log.error('set_channel_assignment(click_channel={0}): invalid argument type'
                #                ''.format(click_channel))
                print('[ERROR] set_channel_assignment(click_channel={0}): invalid argument type'
                      ''.format(click_channel))
                return self.get_channel_assignment()

            # sanity check: all requested channels are available on the device
            all_channels = self.get_all_channels()
            for channel in click_channel_list:
                if channel not in all_channels:
                    # self.log.error('set_channel_assignment(): '
                    #                'click_channel={0} - this channel is not available on the device'
                    #                ''.format(click_channel))
                    print('[ERROR] set_channel_assignment(): '
                          'click_channel={0} - this channel is not available on the device'
                          ''.format(click_channel))
                    return self.get_channel_assignment()

            # If several channel numbers were passed, create virtual Combiner channel
            if len(click_channel_list) > 1:
                self._combiner = TT.Combiner(
                    tagger=self._tagger,
                    channels=click_channel_list
                )
                # Obtain int channel number for the virtual channel
                click_channel_list = [self._combiner.getChannel()]

            # Set new value for click channel
            self._click_channel = int(click_channel_list[0])

        if gate_channel is not None:

            # sanity check: channel is available on the device
            if gate_channel not in self.get_all_channels():
                # self.log.error('set_channel_assignment(): '
                #                'gate_channel={0} - this channel is not available on the device'
                #                ''.format(gate_channel))
                print('[ERROR] set_channel_assignment(): '
                      'gate_channel={0} - this channel is not available on the device'
                      ''.format(gate_channel))
                return self.get_channel_assignment()

            # Set new value for gate channel
            self._gate_channel = int(gate_channel)

        return self.get_channel_assignment()

    def get_all_channels(self):
        """Returns list of all channels available on the device,
        including edge type sign.

        Positive/negative numbers correspond to detection of rising/falling edges.
        For example:
            1 means 'rising edge on connector 1'
            -1 means 'falling edge on connector 1


        :return: (list of int) list of channel numbers including edge sign.
                Example: [-8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8]
                Empty list is returned in the case of error.
        """

        # Sanity check: check that connection to the device was established
        if self._tagger is None:
            # self.log.error('get_all_channels(): not connected to the device yet')
            print('[ERROR] get_all_channels(): not connected to the device yet')
            return []

        channel_list = list(
            self._tagger.getChannelList(TT.TT_CHANNEL_RISING_AND_FALLING_EDGES)
        )
        return channel_list


class GatedCounterService(rpyc.Service):

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
    def exposed_init_counter(self, bin_number):
        return self._module.init_counter(bin_number=bin_number)

    def exposed_close_counter(self):
        return self._module.close_counter()

    def exposed_start_counting(self):
        return self._module.start_counting()

    def exposed_terminate_counting(self):
        return self._module.terminate_counting()

    def exposed_get_status(self):
        return self._module.get_status()

    def exposed_get_count_array(self, timeout=-1):
        res = self._module.get_count_array(timeout=timeout)
        return pickle.dumps(res)


class GatedCounterClient:

    def __init__(self, port, host='localhost'):

        self._connection = rpyc.connect(
            host=host,
            port=port,
            config={'allow_public_attrs': True}
        )

        self._service = self._connection.root

    def init_counter(self, bin_number):
        return self._service.exposed_init_counter(bin_number=bin_number)

    def close_counter(self):
        return self._service.exposed_close_counter()

    def start_counting(self):
        return self._service.exposed_start_counting()

    def terminate_counting(self):
        return self._service.exposed_terminate_counting()

    def get_status(self):
        return self._service.exposed_get_status()

    def get_count_array(self, timeout=-1):
        res_pickle = self._service.exposed_get_count_array(timeout=timeout)
        return pickle.loads(res_pickle)