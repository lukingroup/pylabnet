import abc

class MultiTraceInterface(abc.ABC):

    @abc.abstractmethod
    def set_data(self, x_ar=None, y_ar=None, ind=0, noise=None):
        pass

    @abc.abstractmethod
    def set_lbls(self, x_str=None, y_str=None):
        pass

    @abc.abstractmethod
    def show(self):
        pass


class TraceInterface(abc.ABC):

    @abc.abstractmethod
    def set_data(self, x_ar=None, y_ar=None):
        pass

    @abc.abstractmethod
    def append_data(self, x_ar=None, y_ar=None):
        pass

    @abc.abstractmethod
    def set_lbls(self, x_str=None, y_str=None):
        pass


class HeatMapInterface(abc.ABC):

    @abc.abstractmethod
    def set_data(self, x_ar=None, y_ar=None, z_ar=None):
        pass

    @abc.abstractmethod
    def append_row(self, y_val=None, z_ar=None):
        pass

    @abc.abstractmethod
    def append_col(self, x_val=None, z_ar=None):
        pass

    @abc.abstractmethod
    def set_lbls(self, x_str=None, y_str=None):
        pass


class PBarInterface(abc.ABC):

    @abc.abstractmethod
    def set_value(self, value):
        pass

