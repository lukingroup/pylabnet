

class Optimizer:

    def __init__(self):
        pass


class IQOptimizer(Optimizer):

    def __init(self, awg, sa):
        """ Instantiate IQ optimizer

        :param awg: instance of AWG client
        :param sa: instance of spectrum analyzer client
        """

        self.carrier_freq = None

    def find_peaks(self):
        """ Finds all frequencies and assigns them to attributes """

        do_something
        self.carrier_freq =


awg = Client(..)
sa = Client
iq = IQOptimizer(awg, sa)