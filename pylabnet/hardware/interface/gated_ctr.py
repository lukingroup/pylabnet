import abc


class GatedCtrInterface(abc.ABC):

    @abc.abstractmethod
    def activate_interface(self):
        pass

    @abc.abstractmethod
    def init_ctr(self, bin_number, gate_type):
        """

        :param bin_number:
        :param gate_type: 'RR' and 'RF'
        :return:
        """

    @abc.abstractmethod
    def close_ctr(self):
        pass

    @abc.abstractmethod
    def start_counting(self):
        pass

    @abc.abstractmethod
    def terminate_counting(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        pass

    @abc.abstractmethod
    def get_count_ar(self, timeout=-1):
        pass


class CtrError(Exception):
    pass
