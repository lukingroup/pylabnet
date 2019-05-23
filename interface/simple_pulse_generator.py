import abc


class SimplePGenInterface(abc.ABC):

    @abc.abstractmethod
    def write(self, pb_obj):
        pass

    @abc.abstractmethod
    def cfg_rep(self, rep_numb):
        pass

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        pass
