'''Module checking if measured pulse sequence coincides with desired one'''

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.utils.trace_compare.trace_compare import trace_compare


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
        :x_tol: Allowed deviation in x-diraction of target trace.
        :y_tol: Allowed deviation in y-direction on target trace.
        """

        # Instantiate log
        self.log = LogHandler(logger=logger)

        # Store parameters
        self.pb = pb
        self.sampling_rate = sampling_rate
        self.data_dict = data_dict
        self.x_tol = x_tol
        self.y_tol = y_tol
        self.traces_to_check = data_dict.keys()

        # Check for keys
        self._check_key_assignments()

    def check_traces(self):
        """Check traces"""

        # Turn pulse block into sample dictionary
        sampled_pb = pb_sample(self.pb, samp_rate=self.sampling_rate)

        # Use time time array of data as timebase
        reference_times = np.arange(sampled_pb[1]) / self.sampling_rate

        for trace in self.traces_to_check:
            reference_trace = np.array([reference_times, sampled_pb[0][trace]])
            trace_to_check = self.data_dict[trace]

            trace_compare(
                trace_to_check=trace_to_check,
                reference_trace=reference_trace,
                x_tol=self.x_tol,
                y_tol=self.y_tol
            )
