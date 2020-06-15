"""Generic Module used to compare a measured timestrace with an expected one"""

import scipy.signal as sg
import matplotlib.pyplot as plt
import numpy as np

def trace_compare(trace_to_check, reference_trace, x_tol, y_tol, amplitude=3.3):
    """Compare two timetraces.

    :trace_to_check: (np.array) Trace to check, where the format is as follows:
        np.array([timetrace, valuetrace]), where timetrace contains the timestamps (in s)
        of the values, which are stored in valuetrace.
    :refreference_tracearence_trace: (np.array) The true reference trace following the same format as
        trace_to_check
    :amplitude: (float) Global amplitude to multiply the reference trace with.
    :xtol: Allowed deviation in x-direction of reference trace.
    :ytol: Allowed deviation in y-direction on reference trace.

    Returns number of times the signal under or overshoots.
    """

    # Unpack data
    ref_time, ref_signal = reference_trace[0], reference_trace[1] * amplitude
    check_time, check_signal = trace_to_check[0], trace_to_check[1]

    # Define acceptance region
    max_accept_signal = ref_signal + y_tol
    min_accept_signal = ref_signal - y_tol

    left_timeshift = ref_time - x_tol
    right_timeshift = ref_time + x_tol

    # Rudimentary acceptance plot
    # TODO: Improve this
    fig, ax = plt.subplots()
    ax.plot(ref_time/1e-9, ref_signal, '-', label="Reference")
    ax.plot(check_time/1e-9, check_signal, 'o-', label="Measured")
    ax.plot(right_timeshift/1e-9, min_accept_signal, '-', label="min")
    ax.plot(left_timeshift/1e-9, max_accept_signal, '-', label="max")
    #ax.fill_between(left_timeshift, max_accept_signal, 3.3)
    ax.set_xlabel("Time since trigger [ns]")
    ax.set_ylabel("Signal [V]")
    plt.legend()
    plt.show()

    # Very rudimentary: Count timing violations
    # TODO: Improve this
    num_signal_overshoot = np.sum(check_signal > max_accept_signal)
    num_signal_undershoot = np.sum(check_signal < max_accept_signal)

    return num_signal_undershoot, num_signal_overshoot




