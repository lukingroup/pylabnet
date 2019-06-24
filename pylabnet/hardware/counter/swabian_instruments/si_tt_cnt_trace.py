import TimeTagger as TT
import time
import copy
import pickle
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.gated_ctr import GatedCtrError
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class SITTCntTrace:

    def __init__(self, tagger, click_ch, start_ch, logger=None):
        """Instantiate gated counter

        :param tagger:
        :param click_ch: (int|list of int) clicks on all specified channels
                              will be summed into one logical channel
        :param start_ch: (int) start trigger channel number
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
        #   length of returned 1D count array, the size of allocated memory buffer.
        # must be given as argument of init_ctr() call
        self._bin_n = 0

        # Channel assignments
        self._click_ch = 0
        self._start_ch = 0
        # reference to Combiner object
        #   (if _click_ch is a list - then counts on all channels are summed
        #   into virtual channel - self._combiner.getChannel())
        self._combiner = None
        # apply channel assignment
        self.set_ch_assignment(
            click_ch=click_ch,
            start_ch=start_ch
        )

    # ---------------- Interface ---------------------------

    def activate_interface(self):
        return 0

    def init_ctr(self, bin_n, bin_w):

        bin_w = int(bin_w / 1e-12)

        # Close existing counter, if it was initialized before
        self.close_ctr()

        # Instantiate counter measurement
        try:
            self._ctr = TT.TimeDifferences(
                tagger=self._tagger,
                click_channel=self._click_ch,
                start_channel=self._start_ch,
                n_bins=bin_n,
                binwidth=bin_w
            )

            # save bin_number in internal variable
            self._bin_n = bin_n

        # handle NotImplementedError (typical error, produced by TT functions)
        except NotImplementedError:
            # remove reference to the counter measurement
            self._ctr = None

            msg_str = 'init_ctr(): instantiation of TimeDifferences measurement failed'
            self.log.error(msg_str=msg_str)
            raise GatedCtrError(msg_str)

        # Prepare counter to be started by start_counting()
        # (TimeDifferences measurement starts running immediately after instantiation,
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

        return 0

    def start_counting(self):

        # Try stopping and restarting counter measurement
        try:
            self._ctr.stop()  # does not fail even if the measurement is not running
            self._ctr.clear()
            self._ctr.start()

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
            raise GatedCtrError(msg_str)

    def stop_counting(self):

        # Try stopping counter measurement
        try:
            # stop counter
            self._ctr.stop()

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
            raise GatedCtrError(msg_str)

    def get_count_trace(self):
        return self._ctr.getData()[0]

    # ------------------------------------------------------

    def get_ch_assignment(self):
        """Returns dictionary containing current channel assignment:
            {
                'click_ch': (int) click_channel_number_including_edge_sign
                'gate_ch': (int) gate_channel_number_including_edge_sign
            }

        :return: dict('click_ch': _, 'gate_ch': _)
        """

        click_ch = copy.deepcopy(self._click_ch)
        start_ch = copy.deepcopy(self._start_ch)

        return dict(click_ch=click_ch, start_ch=start_ch)

    def set_ch_assignment(self, click_ch=None, start_ch=None):
        """Sets click channel and and gate channel.

        This method only changes internal variables
        self._click_ch and self._gate_ch.
        To apply the channel update, call  init_ctr() again.


        :param click_ch: (int|list of int) click channel number
                              positive/negative values - rising/falling edge detection
                              if list is given, clicks on all specified channels
                              will be merged into one logic channel

        :param start_ch: (int) channel number
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
                raise GatedCtrError(msg_str)

            # sanity check: all requested channels are available on the device
            all_chs = self.get_all_chs()
            for channel in click_ch_list:
                if channel not in all_chs:
                    msg_str = 'set_ch_assignment(): '\
                              'click_ch={0} - this channel is not available on the device'\
                              ''.format(click_ch)
                    self.log.error(msg_str=msg_str)
                    raise GatedCtrError(msg_str)

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

        if start_ch is not None:

            # sanity check: channel is available on the device
            if start_ch not in self.get_all_chs():
                msg_str = 'set_ch_assignment(): '\
                          'start_ch={0} - this channel is not available on the device'\
                          ''.format(start_ch)
                self.log.error(msg_str=msg_str)
                raise GatedCtrError(msg_str)

            # Set new value for gate channel
            self._start_ch = int(start_ch)

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
            raise GatedCtrError(msg_str)

        channel_list = list(
            self._tagger.getChannelList(TT.TT_CHANNEL_RISING_AND_FALLING_EDGES)
        )
        return channel_list


class SITTCntTraceService(ServiceBase):

    def exposed_activate_interface(self):
        return self._module.activate_interface()

    def exposed_init_ctr(self, bin_n, bin_w):
        return self._module.init_ctr(
            bin_n=bin_n,
            bin_w=bin_w
        )

    def exposed_close_ctr(self):
        return self._module.close_ctr()

    def exposed_start_counting(self):
        return self._module.start_counting()

    def exposed_stop_counting(self):
        return self._module.stop_counting()

    def exposed_get_count_trace(self):
        res = self._module.get_count_trace()
        return pickle.dumps(res)


class SITTCntTraceClient(ClientBase):

    def activate_interface(self):
        return self._service.exposed_activate_interface()

    def init_ctr(self, bin_n, bin_w):
        return self._service.exposed_init_ctr(
            bin_n=bin_n,
            bin_w=bin_w
        )

    def close_ctr(self):
        return self._service.exposed_close_ctr()

    def start_counting(self):
        return self._service.exposed_start_counting()

    def stop_counting(self):
        return self._service.exposed_stop_counting()

    def get_count_trace(self):
        res_pickle = self._service.exposed_get_count_trace()
        return pickle.loads(res_pickle)
