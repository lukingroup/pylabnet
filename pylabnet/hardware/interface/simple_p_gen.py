import abc


class SimplePGenInterface(abc.ABC):

    @abc.abstractmethod
    def activate_interface(self):
        pass

    @abc.abstractmethod
    def write(self, pb_obj, step_adj=True):
        pass

    @abc.abstractmethod
    def set_rep(self, rep_num):
        pass

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        """Get status of the device

        0 - 'Idle'
        1 - 'Running'
        Exception is produced in the case of any error
        (for example, connection to the device is lost)

        :return: (int) status code
                 Exception is produced in the case of error
        """

        pass


class PGenError(Exception):
    pass
