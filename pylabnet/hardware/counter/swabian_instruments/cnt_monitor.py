import TimeTagger as TT
import time
import copy
import pickle
import numpy as np
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.hardware.interface.ctr_monitor import CtrMonitorInterface, CtrError
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class Wrap():

    def __init__(self, tagger, ch_list=[1], logger=None):
        """Instantiate count monitor

        :param tagger: instance of TimeTagger class
        :param ch_list: list of channels to count
        :param logger: instance of LogClient class
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

        # Counter instance
        self._ctr = None

        # Set click channels
        self._ch_list = ch_list
        self.set_ch_assignment(ch_list=ch_list)

    def start_ctr(self, bin_width=1000000000, n_bins=10000):
        """Start counter

        :param binwidth: integer in ps for width of count bins
        :param n_values: integer number of bins to store before
                            wrapping around
        """
        
        # Instantiate Counter instance, see TT documentation
        self._ctr = TT.Counter(
            self._tagger, 
            channels=self._ch_list, 
            binwidth=bin_width, 
            n_values=n_bins
        )

    def clear_ctr(self):
        """Resets the array to zero and restarts the measurement.
            See the clear() method of Counter class in TT
        """

        # Clear counter (see TT documentation)
        self._ctr.clear()

    def get_counts(self):
        """Gets a 2D array of counts on all channels. See the 
            getData() method of Counter class in TT
        """

        # Get count data (see TT documentation)
        return self._ctr.getData()

    def get_x_axis(self):
        """Gets the x axis in picoseconds for the count array.
            See the getIndex() method of Counter class in TT
        """

        # Get x axis
        return self._ctr.getIndex()

    def set_ch_assignment(self, ch_list=[1]):
        """Sets the ch_list attribute of the wrapper to a valid
            list of channel numbers as desired by TT, also 
            configures the default naming convention for channels

        :param ch_list: list of integer numbers of channels,
                        following the convention 1 ... 8
                        for rising edge and negative for falling
        """

        # Set channel notation as desired
        TT.setTimeTaggerChannelNumberScheme(
            TT.TT_CHANNEL_NUMBER_SCHEME_ONE
        )

        """  # Assign channel number to wrapper attribute
        # First take single integer values and place them in a
        # list
        if type(ch_list) == int:
            to_set_list = [ch_list]

        # Now pass through lists
        elif type(ch_list) == list:
            to_set_list = ch_list

        # Identify other types and terminate
        else:
            err_string = 'Wrong data type for channel list input! \n' \
                         'Valid types are: Int, and List[Int] \n' \
                         'You used '
            err_string_2 = str(type(ch_list))
            err_string_out = err_string + err_string_2
            self.log.error(msg_str=err_string_out)
            raise CtrError(err_string_out)

        # Check the properties of the list
        if max(ch_list) > 8 or min(ch_list) < -8:
            err_string = 'ch_list values must be in the ranges: \n' \
                         '[-8,1] and [1,8]'
            self.log.error(msg_str=err_string)
            raise CtrError(err_string)

        if len(ch_list) > 8:
            err_string = 'ch_list length exceeds number of channels'
            self.log.error(msg_str=err_string)
            raise CtrError(err_String) """

        # Set attribute to validated ch_list
        self._ch_list = ch_list

class Service(ServiceBase):

    def exposed_start_counting(self, bin_width=1000000000, n_bins=10000):
        return self._module.start_ctr(
            bin_width=bin_width,
            n_bins=n_bins
        )

    def exposed_clear_counter(self):
        return self._module.clear_ctr()

    def exposed_get_counts(self):
        res_pickle = self._module.get_counts()
        return pickle.dumps(res_pickle)

    def exposed_get_x_axis(self):
        res_pickle = self._module.get_x_axis()
        return pickle.dumps(res_pickle)

    def exposed_set_channels(self, ch_list=[1]):
        return self._module.set_ch_assignment(
            ch_list=ch_list
        )


class Client(ClientBase):

    def start_counting(self, bin_width=1000000000, n_bins=10000):
        return self._service.exposed_start_counting(
            bin_width=bin_width,
            n_bins=n_bins
        )

    def clear_counter(self):
        return self._service.exposed_clear_counter()

    def get_counts(self):
        res_pickle = self._service.exposed_get_counts()
        return pickle.loads(res_pickle)

    def get_x_axis(self):
        res_pickle = self._service.exposed_get_x_axis()
        return pickle.loads(res_pickle)

    def set_channels(self, ch_list=[1]):
        return self._service.exposed_set_channels(
            ch_list=ch_list
        )