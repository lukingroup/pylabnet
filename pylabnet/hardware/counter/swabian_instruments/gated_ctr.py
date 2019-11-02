import TimeTagger as TT
import time
import copy
import pickle
import numpy as np
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface, CtrError
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class Wrap(GatedCtrInterface):

    def __init__(self, tagger, click_ch, gate_ch, logger=None):
        """Instantiate gated counter

        :param tagger: instance of TimeTagger class
        :param click_ch: (int|list of int) clicks on all specified channels
                                    will be summed into one logical channel
        :param gate_ch: (int) positive/negative channel number - count while
                             gate is high/low
        """

        # Log
        self.log = LogHandler(logger=logger)

        # Reference to tagger
        self._tagger = tagger

        # Log device ID information to demonstrate that connection indeed works
        serial = self._tagger.getSerial()
        model = self._tagger.getModel()
        self.log.info(
            'Got reference to Swabian Instruments TimeTagger device \n'
            'Serial number: {0}, Model: {1}'
            ''.format(serial, model)
        )

        # Gated Counter
        # reference to the TT.CountBetweenMarkers measurement instance
        self._ctr = None
        # number of count bins:
        #   length of returned 1D count array, the expected number of gate pulses,
        #   the size of allocated memory buffer.
        # must be given as argument of init_ctr() call
        self._bin_number = 0

        # Channel assignments
        self._click_ch = 0
        self._gate_ch = 0
        # reference to Combiner object
        #   (if _click_ch is a list - then counts on all channels are summed
        #   into virtual channel - self._combiner.getChannel())
        self._combiner = None
        # apply channel assignment
        self.set_ch_assignment(
            click_ch=click_ch,
            gate_ch=gate_ch
        )

        # Module status code
        #  -1 "void"
        #   0 "idle"
        #   1 "in_progress"
        #   2 "finished"
        self._status = -1
        self._set_status(-1)

        # Once __init__() call is complete,
        # the counter is ready to be initialized by the above-lying logic though init_ctr() call

    # ---------------- Interface ---------------------------

    def activate_interface(self):
        return 0

    def init_ctr(self, bin_number, gate_type):

        # Device-specific fix explanation:
        #
        #   CountBetweenMarkers measurement configured for n_value bins
        #   indeed fills-up buffer after n_value gate pules, but call of
        #   self._ctr.ready() still gives False. Only after one additional
        #   gate pulse it gives True, such that self.get_status()
        #   gives 2 and self.get_count_ar() returns:
        #
        #       device always needs an additional pulse to complete
        #       (even for n_values = 1 it needs 2 gate pulses).
        #
        #   Since this is very counter-intuitive and confuses
        #   above-lying logic, a fix is made here:
        #
        #       For given bin_number, CountBetweenMarkers measurement
        #       is instantiated with n_values = (bin_number - 1) such
        #       that it completes after receiving bin_number physical
        #       gate pulses as expected.
        #
        #       As a result, in the returned count_ar
        #       (still of length bin_number, as logic expects), the last
        #       value is just a copy of (bin_number - 1)-st element.
        #
        #   The last physical bin is not actually measured, what can lead
        #   to confusions when bin_number is on the order of one.
        #   The warning below reminds about it:
        if bin_number <= 5:
            self.log.warn(
                'init_ctr(): due to strange behaviour of TT.CountBetweenMarkers '
                'measurement, this driver makes a hack: counter is configured to '
                'measure bin_number-1 pulses and the last element of the returned '
                'count_ar is just a copy of the preceding one. \n'
                'With bin_number={}, only the first {} gate windows will actually be '
                'measured.'
                ''.format(bin_number, bin_number - 1)
            )

        # Close existing counter, if it was initialized before
        if self.get_status() != -1:
            self.close_ctr()

        # Instantiate counter measurement
        try:
            if gate_type == 'RF':
                self._ctr = TT.CountBetweenMarkers(
                    tagger=self._tagger,
                    click_channel=self._click_ch,
                    begin_channel=self._gate_ch,
                    end_channel=-self._gate_ch,
                    n_values=bin_number - 1
                )
            elif gate_type == 'RR':
                self._ctr = TT.CountBetweenMarkers(
                    tagger=self._tagger,
                    click_channel=self._click_ch,
                    begin_channel=self._gate_ch,
                    n_values=bin_number - 1
                )
            else:
                msg_str = 'init_ctr(): unknown gate type "{}" \n' \
                          'Valid types are: \v' \
                          '     "RR" - Raising-Raising \n' \
                          '     "RF" - Raising-Falling'
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

            # set status to "idle"
            self._set_status(0)

            # save bin_number in internal variable
            self._bin_number = bin_number

        # handle NotImplementedError (typical error, produced by TT functions)
        except NotImplementedError:
            # remove reference to the counter measurement
            self._ctr = None
            # set status to "void"
            self._set_status(-1)

            msg_str = 'init_ctr(): instantiation of CountBetweenMarkers measurement failed'
            self.log.error(msg_str=msg_str)
            raise CtrError(msg_str)

        # Prepare counter to be started by start_counting()
        # (CountBetweenMarkers measurement starts running immediately after instantiation,
        # so it is necessary to stop it and erase all counts collected between instantiation and stop() call)
        self._ctr.stop()
        self._ctr.clear()

        return 0

    def close_ctr(self):

        # Try to stop and to clear TT.CountBetweenMarkers measurement instance
        try:
            self._ctr.stop()
            self._ctr.clear()
        except:
            pass

        # Remove reference, set status to "void"
        self._ctr = None
        self._set_status(-1)

        return 0

    def start_counting(self):

        current_status = self.get_status()

        # Sanity check: ensure that counter is not "void"
        if current_status == -1:
            msg_str = 'start_counting(): ' \
                      'counter is in "void" state - it ether was not initialized or was closed. \n' \
                      'Initialize it by calling init_ctr()'
            self.log.error(msg_str=msg_str)
            raise CtrError(msg_str)

        # Terminate counting if it is already running
        if current_status == 1:
            self.terminate_counting()

        # Try stopping and restarting counter measurement
        try:
            self._ctr.stop()  # does not fail even if the measurement is not running
            self._ctr.clear()
            self._ctr.start()

            # set status to "in_progress"
            self._set_status(1)

            # Wait until the counter is actually ready to count
            time.sleep(0.1)

            return 0

        # handle exception in TT function calls [NotImplementedError]
        except NotImplementedError:
            # Since stop() and clear() methods are very robust,
            # this part is only executed if counter is totally broken.
            # In this case it makes sense to close counter.
            self.close_ctr()

            msg_str = 'start_counting(): call failed. Counter was closed. \n'\
                      'Re-initialize counter by calling init_ctr() again'
            self.log.error(msg_str=msg_str)
            raise CtrError(msg_str)

    def terminate_counting(self):

        # Action of this method is non-trivial for "in_progress" state only
        if self.get_status() != 1:
            return 0

        # Try stopping and clearing counter measurement
        try:
            # stop counter, clear count array
            self._ctr.stop()
            self._ctr.clear()

            # set status to "idle"
            self._set_status(0)
            return 0

        # handle exception in TT.stop()/TT.clear()
        except NotImplementedError:
            # Since stop() and clear() methods are very robust,
            # this part is only executed if counter is totally broken.
            # In this case it makes sense to close counter.
            self.close_ctr()

            msg_str = 'terminate_counting(): call failed. Counter was closed. \n' \
                      'Re-initialize it by calling init_ctr()'
            self.log.error(msg_str=msg_str)
            raise CtrError(msg_str)

    def get_status(self):

        # Check that counter measurement was initialized and that the connection works
        # by calling isRunning()
        #  -- if self._ctr is None or if connection is broken, call will rise some
        #     exception. In this case "void" status should be set
        #  -- if counter was initialized and connection works, it will return successfully
        #     (True or False, but the result does not matter)
        #     and further choice between "idle", "in_progress", and "finished" should be made
        try:
            self._ctr.isRunning()
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
            if self._ctr.ready():

                self._ctr.stop()
                self._status = 2

        return copy.deepcopy(self._status)

    def get_count_ar(self, timeout=-1):

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
                self._ctr.getData(),
                dtype=np.uint32
            )

            # Fix of the issue with an additional gate pulse needed to complete
            # measurement (see comment in init_ctr() for explanation):
            #   the last element of returned array is just a copy
            #   of the last physically measured bin
            count_array = np.append(count_array, count_array[-1])

            return count_array

        # return empty list for all other states ("in_progress", "idle", and "void")
        else:
            if status == 1:
                self.log.warn(
                    'get_count_ar(): operation timed out, but counter is still running. \n'
                    'Try calling get_count_ar() later or terminate process by terminate_counting().'
                )
            elif status == 0:
                self.log.warn('get_count_ar(): counter is "idle" - nothing to read')
            else:
                msg_str = 'get_count_ar(): counter broke and was deleted \n' \
                          'Re-initialize it by calling init_ctr()'
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

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
        # by calling close_ctr()
        if new_status == -1:
            self._status = -1
            return 0

        # Transition to "idle" is possible from
        #   "void" by calling init_ctr()
        #   "in_progress" by calling terminate_counting()
        if new_status == 0:
            if self._status == -1 or self._status == 1:
                self._status = 0
                return 0
            else:
                msg_str = '_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'\
                          'Counter status was not changed.'\
                          ''.format(new_status, self._status)
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

        # Transition to "in_progress" is possible from
        #   "idle" by calling start_counting()
        #   "finished" by calling start_counting()
        if new_status == 1:
            if self._status == 0 or self._status == 2:
                self._status = 1
                return 0
            else:
                msg_str = '_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'\
                          'Counter status was not changed.'\
                          ''.format(new_status, self._status)
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

        # Transition to "finished" is only possible from "in_progress"
        # by successful completion of count_array accumulation
        if new_status == 2:
            if self._status == 1:
                self._status = 2
                return 0
            else:
                msg_str = '_set_status(): transition to new_status={0} from self._status={1} is impossible. \n'\
                          'Counter status was not changed.'\
                          ''.format(new_status, self._status)
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

    def get_ch_assignment(self):
        """Returns dictionary containing current channel assignment:
            {
                'click_ch': (int) click_channel_number_including_edge_sign
                'gate_ch': (int) gate_channel_number_including_edge_sign
            }

        :return: dict('click_ch': _, 'gate_ch': _)
        """

        click_ch = copy.deepcopy(self._click_ch)
        gate_ch = copy.deepcopy(self._gate_ch)

        return dict(click_ch=click_ch, gate_ch=gate_ch)

    def set_ch_assignment(self, click_ch=None, gate_ch=None):
        """Sets click channel and and gate channel.

        This method only changes internal variables
        self._click_ch and self._gate_ch.
        To apply the channel update, call  init_ctr() again.


        :param click_ch: (int|list of int) click channel number
                              positive/negative values - rising/falling edge detection
                              if list is given, clicks on all specified channels
                              will be merged into one logic channel

        :param gate_ch: (int) channel number
                             positive/negative - count during high/low gate level

        :return: (dict) actually channel assignment:
                        {
                            'click_channel': (int) click_chnl_num,
                            'gate_channel': (int) gate_chnl_num
                        }
        """

        if click_ch is not None:
            # for convenience bring int type of input to list of int
            if isinstance(click_ch, list):
                click_ch_list = click_ch
            elif isinstance(click_ch, int):
                click_ch_list = [click_ch]
            else:
                # unknown input type
                msg_str = 'set_ch_assignment(click_ch={0}): invalid argument type'\
                          ''.format(click_ch)
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

            # sanity check: all requested channels are available on the device
            all_chs = self.get_all_chs()
            for channel in click_ch_list:
                if channel not in all_chs:
                    msg_str = 'set_ch_assignment(): '\
                              'click_ch={0} - this channel is not available on the device'\
                              ''.format(click_ch)
                    self.log.error(msg_str=msg_str)
                    raise CtrError(msg_str)

            # If several channel numbers were passed, create virtual Combiner channel
            if len(click_ch_list) > 1:
                self._combiner = TT.Combiner(
                    tagger=self._tagger,
                    channels=click_ch_list
                )
                # Obtain int channel number for the virtual channel
                click_ch_list = [self._combiner.getChannel()]

            # Set new value for click channel
            self._click_ch = int(click_ch_list[0])

        if gate_ch is not None:

            # sanity check: channel is available on the device
            if gate_ch not in self.get_all_chs():
                msg_str = 'set_ch_assignment(): '\
                          'gate_ch={0} - this channel is not available on the device'\
                          ''.format(gate_ch)
                self.log.error(msg_str=msg_str)
                raise CtrError(msg_str)

            # Set new value for gate channel
            self._gate_ch = int(gate_ch)

        return self.get_ch_assignment()

    def get_all_chs(self):
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
            msg_str = 'get_all_chs(): not connected to the device yet'
            self.log.error(msg_str=msg_str)
            raise CtrError(msg_str)

        channel_list = list(
            self._tagger.getChannelList(TT.TT_CHANNEL_RISING_AND_FALLING_EDGES)
        )
        return channel_list


class Service(ServiceBase):

    def exposed_activate_interface(self):
        return self._module.activate_interface()

    def exposed_init_ctr(self, bin_number, gate_type):
        return self._module.init_ctr(
            bin_number=bin_number,
            gate_type=gate_type
        )

    def exposed_close_ctr(self):
        return self._module.close_ctr()

    def exposed_start_counting(self):
        return self._module.start_counting()

    def exposed_terminate_counting(self):
        return self._module.terminate_counting()

    def exposed_get_status(self):
        return self._module.get_status()

    def exposed_get_count_ar(self, timeout=-1):
        res = self._module.get_count_ar(timeout=timeout)
        return pickle.dumps(res)


class Client(ClientBase, GatedCtrInterface):

    def activate_interface(self):
        return self._service.exposed_activate_interface()

    def init_ctr(self, bin_number, gate_type):
        return self._service.exposed_init_ctr(
            bin_number=bin_number,
            gate_type=gate_type
        )

    def close_ctr(self):
        return self._service.exposed_close_ctr()

    def start_counting(self):
        return self._service.exposed_start_counting()

    def terminate_counting(self):
        return self._service.exposed_terminate_counting()

    def get_status(self):
        return self._service.exposed_get_status()

    def get_count_ar(self, timeout=-1):
        res_pickle = self._service.exposed_get_count_ar(timeout=timeout)
        return pickle.loads(res_pickle)
