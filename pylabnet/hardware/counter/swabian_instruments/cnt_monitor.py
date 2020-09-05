""" Hardware wrapper for Swabian Instruments TimeTagger, including client and server access classes """

import TimeTagger as TT
import pickle
import socket
from pylabnet.utils.logging.logger import LogHandler


class Wrap:

    def __init__(self, tagger, logger=None):
        """Instantiate count monitor

        :param tagger: instance of TimeTagger class
        :param ch_list: list of channels to count
        :param logger: instance of LogClient class, optional
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
        self._ctr = {}

        # Set click channels
        self._ch_list = {}

    def start_ctr(self, name=None, bin_width=1000000000, n_bins=10000):
        """Start counter

        :param name: (str) identifier for the counter measurement
        :param bin_width: integer in ps for width of count bins
        :param n_bins: integer number of bins to store before
                            wrapping around
        """

        # If a name is not provided just use the index of the measurement
        if name is None:
            name = str(len(self._ctr))

        # Instantiate Counter instance, see TT documentation
        self._ctr[name] = TT.Counter(
            self._tagger,
            channels=self._ch_list,
            binwidth=bin_width,
            n_values=n_bins
        )

    def clear_ctr(self, name=None):
        """Resets the array to zero and restarts the measurement.
            See the clear() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Clear counter (see TT documentation)
        self._ctr[name].clear()

    def get_counts(self, name=None):
        """Gets a 2D array of counts on all channels. See the
            getData() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Get count data (see TT documentation)
        return self._ctr[name].getData()

    def get_x_axis(self, name=None):
        """Gets the x axis in picoseconds for the count array.
            See the getIndex() method of Counter class in TT

        :param name: (str) identifier for the counter measurement
        """

        name = self.handle_name(name)

        # Get x axis
        return self._ctr[name].getIndex()

    def set_ch_assignment(self, name=None, ch_list=[1]):
        """Sets the ch_list attribute of the wrapper to a valid
            list of channel numbers as desired by TT, also
            configures the default naming convention for channels

        :param name: (str) identifier for the counter measurement
        :param ch_list: list of integer numbers of channels,
                        following the convention 1 ... 8
                        for rising edge and negative for falling
        """

        if name is None:
            name = str(len(self._ctr))

        # Set attribute to validated ch_list
        self._ch_list[name] = ch_list

    @staticmethod
    def handle_name(name):
        if name is None:
            return '0'
        else:
            return name
