"""Generic Module used to compare a measured timestrace with an expected one"""

from pylabnet.gui.igui.iplot import MultiTraceFig


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

    # TODO: Use time lag analysis to overlay traces

    # Define acceptance region
    max_accept_signal = ref_signal + y_tol
    min_accept_signal = ref_signal - y_tol

    left_timeshift = ref_time - x_tol
    right_timeshift = ref_time + x_tol

    ch_names = ["Reference", "Measured", "min", "max"]
    multi_trace = MultiTraceFig(ch_names=ch_names)

    multi_trace.set_data(ref_time/1e-9, ref_signal, 0)
    multi_trace.set_data(check_time/1e-9, check_signal, 1)
    multi_trace.set_data(right_timeshift/1e-9, min_accept_signal, 2)
    multi_trace.set_data(left_timeshift/1e-9, max_accept_signal, 3)

    multi_trace.set_lbls(
        x_str='Time since trigger [ns]',
        y_str='Signal [V]'
    )

    multi_trace.show()

    # TODO: Perform timing violation check.
