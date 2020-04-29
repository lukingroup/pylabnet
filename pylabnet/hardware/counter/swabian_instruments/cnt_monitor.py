""" Hardware wrapper for Swabian Instruments TimeTagger, including client and server access classes """

import TimeTagger as TT
import pickle
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase
from pylabnet.core.generic_server import GenericServer


class Wrap:

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

        :param bin_width: integer in ps for width of count bins
        :param n_bins: integer number of bins to store before
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


def launch(**kwargs):
    """ Connects to SI TT and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """
    DEFAULT_CH_LIST = [1]

    TT.setTimeTaggerChannelNumberScheme(TT.TT_CHANNEL_NUMBER_SCHEME_ONE)

    # Connect to the device, otherwise instantiate virtual connection
    try:
        tagger = TT.createTimeTagger()
    except RuntimeError:
        kwargs['logger'].warn('Failed to connect to Swabian Instruments Time Tagger.'
                              ' Instantiating virtual device instead')
        tagger = TT.createTimeTaggerVirtual()

    cnt_trace_wrap = Wrap(
        tagger=tagger,
        ch_list=DEFAULT_CH_LIST,
        logger=kwargs['logger']
    )

    # Instantiate Server
    cnt_trace_service = Service()
    cnt_trace_service.assign_module(module=cnt_trace_wrap)
    cnt_trace_service.assign_logger(logger=kwargs['logger'])
    cnt_trace_server = GenericServer(
        service=cnt_trace_service,
        host='localhost',
        port=kwargs['port']
    )
    cnt_trace_server.start()
