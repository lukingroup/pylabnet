'''Module checking if measured pulse sequence coincides with desired one'''

from pylabnet.utils.logging.logger import LogHandler
import numpy as np

class PbChecker():

    def _check_key_assignments(self):
        """Check if key values in data dict coincide with keys in pulseblock"""

        if not self.data_dict.keys() == self.pb.p_dict.keys():
            for assignment_key in self.data_dict.keys():
                if assignment_key not in self.pb.p_dict.keys():
                    self.log.error(
                        f"Key '{assignment_key}' in assignment dictionary not found in pulseblock instance. Available keys are {self.pb.p_dict.keys()}."
                    )
            for pb_key in self.pb.p_dict.keys():
                if pb_key not in self.data_dict.keys():
                    self.log.info(
                        f"Key '{pb_key}' in pulseblock instance not found in assignment dictionary, will not be checked."
                    )
        else:
            self.log.info('Will check all traces.')


    def __init__(self, pb, sampling_rate, data_dict, x_tol, y_tol, logger):
        """Initialize the pulseblock checker instance.

        :pb: (object) Pulseblock object
        :sampling_rate: Sampling rate of pulse sequence
        :data_dict: (dictionary) Dictionary containign as keys the trace names
            according to pulseblock objects, and as values a np.array
            containing the measured trace in the folllowing form: [x_values, y_values],
            where x_values and y_values are np.arrays.
        :xtol: Allowed deviation in x-diraction of target trace.
        :ytol: Allowed deviation in y-direction on target trace.
        """

         # Instantiate log
        self.log = LogHandler(logger=logger)

        self.pb = pb
        self.data_dict = data_dict
        self.x_tol = x_tol
        self.y_tol = y_tol

        data_dict.keys()

        # Check for keys
        self._check_key_assignments()



