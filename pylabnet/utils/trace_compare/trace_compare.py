"""Generic Module used to compare a measured timestrace with an expected one"""

import scipy.signal as sg
import matplotlib.pyplot as plt
import numpy as np

def trace_compare(trace_to_check, reference_trace, x_tol, y_tol, amplitude=3.3):
    """Compare two timetraces.

    :trace_to_check: (np.array) Trace to check, where the format is as follows:
        np.array([timetrace, valuetrace]), where timetrace contains the timestamps (in s)
        of the values, which are stored in valuetrace.
    :refarence_trace: (np.array) The true reference trace following the same format as
        trace_to_check
    :amplitude: (float) Global amplitude to multiply the reference trace with.
    :xtol: Allowed deviation in x-direction of reference trace.
    :ytol: Allowed deviation in y-direction on reference trace.
    """

    # Unpack data
    ref_time, ref_signal = reference_trace[0], reference_trace[1] * amplitude
    check_time, check_signal = trace_to_check[0], trace_to_check[1]

    # Define acceptance region
    max_acceptance_singnal = ref_signal + y_tol


    plt.figure()
    plt.plot(ref_time/1e-9, ref_signal, 'o-', label="Reference Trace")
    plt.plot(check_time/1e-9, check_signal, 'o-', label="Check Trace")
    plt.show()



