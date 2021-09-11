import abc


class CtrMonitorInterface(abc.ABC):

    @abc.abstractmethod
    def start_counting(self, bin_width=1000000000, n_bins=10000):
        """

        :param bin_width: Width of counting bins
        :param n_values: Number of values of counter array
        """

    @abc.abstractmethod
    def clear_counter(self):
        pass

    @abc.abstractmethod
    def get_counts(self):
        pass

    @abc.abstractmethod
    def get_x_axis(self):
        pass

        """

        :param ch_list: List of channels to count
        """

    @abc.abstractmethod
    def set_channels(self, ch_list=[1]):
        """

        :param ch_list: List of channels to use [1,8] for
            rising edges and [-8,-1] for falling edges
        """


class CtrError(Exception):
    pass
