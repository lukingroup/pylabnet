import abc


class MWSrcInterface(abc.ABC):

    @abc.abstractmethod
    def activate_interface(self):
        pass

    @abc.abstractmethod
    def on(self):
        pass

    @abc.abstractmethod
    def off(self):
        pass

    @abc.abstractmethod
    def get_freq(self):
        pass

    def set_freq(self, freq):
        pass

    def set_freq_swp(self, start, stop, n_pts):
        pass

    @abc.abstractmethod
    def get_pwr(self):
        pass

    @abc.abstractmethod
    def set_pwr(self, pwr):
        pass

    @abc.abstractmethod
    def get_mode(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        pass
