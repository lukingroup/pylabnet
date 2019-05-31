import abc


class MWSrcInterface(abc.ABC):

    @abc.abstractmethod
    def activate_interface(self):
        pass

    # Output control

    @abc.abstractmethod
    def on(self):
        pass

    @abc.abstractmethod
    def off(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        pass

    # Power

    @abc.abstractmethod
    def get_pwr(self):
        pass

    @abc.abstractmethod
    def set_pwr(self, pwr):
        pass

    # Frequency

    @abc.abstractmethod
    def get_freq(self):
        pass

    @abc.abstractmethod
    def set_freq(self, freq):
        pass

    @abc.abstractmethod
    def set_freq_swp(self, start, stop, n_pts):
        pass

    @abc.abstractmethod
    def get_mode(self):
        pass

