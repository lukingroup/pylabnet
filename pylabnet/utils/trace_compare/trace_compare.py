"""Generic Module used to compare a measured timestrace with an expected one"""


def trace_compare(trace_to_check, reference_trace, x_tol, y_tol):
    """Compare two timetraces.

    :trace_to_check: (np.array) Trace to check, where the format is as follows:
        np.array([timetrace, valuetrace]), where timetrace contains the timestamps (in s)
        of the values, which are stored in valuetrace.
    :refarence_trace: (np.array) The true reference trace following the same format as
        trace_to_check
    :xtol: Allowed deviation in x-direction of reference trace.
    :ytol: Allowed deviation in y-direction on reference trace.
    """
    pass