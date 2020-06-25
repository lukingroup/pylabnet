import numpy as np


def pb_sample(pb_obj, samp_rate, len_min=0, len_max=float('inf'), len_step=1, len_adj=True, debug=False):
    """ Generate sample array.

    Unlike PulseBlock class, which makes now assumptions beyond the base class
    attributes, this function introduces one more requirement:
        each Pulse and DfltPulse object in the block must have
        get_value(t_ar) method with the following signature:
            :param t_ar: (numpy.array) array of time points
            :return: (numpy.array) array of samples

    :param pb_obj: (PulseBlock) pulse block to be sampled
    :param samp_rate: (float) sampling rate [Hz]

    Hardware memory waveform-length limitations

    :param len_min: (int) minimal waveform length (used for sanity check and
    auto-padding if len_adj is set to True)

    :param len_max: (int) maximal waveform length (used for sanity check only)

    :param len_step: (int) waveform length granularity (if length must be an
    integer multiple of a given step)

    :param len_adj: (bool) if True, sample array will be padded with default
    values (determined by pb_odj.dflt_dict) to meet len_min and len_step.
    If False and resulting sample array length does not meet these constraints,
    ValueError will be produced. Note that if length exceeds len_max, ValueError
    is always produced.

    :param debug: (bool) if True, time-point array will be included as a last
    element in the returned tuple

    :return: (tuple)
    (
        samp_dict = {'ch_name': sample_array, ...}
        n_pts - number of samples (per channel, number of time points)
        add_pts - number of default points added to meet len_min and len_step
        [t_ar] (if debug is set to True) - numpy float array of time points
    )
    """

    t_step = 1 / samp_rate
    # Number of samples
    n_pts = int(
        (pb_obj.dur - 0.5*t_step) // t_step + 1
    )
    # '- 0.5*t_step' is added to make actual duration of the waveform to be
    # as close to pb_obj.dur as possible.
    #
    # Normally a waveform-generation device quickly updates output value and
    # keeps it constant for 1/samp_rate interval, then updates output to the
    # new value, and so on. That is why it is impossible to obtain arbitrary
    # duration of the actual waveform - the minimal step is 1/samp_rate.
    #
    # Subtraction of half-step from pb_obj.dur ensures that integer division
    # plus one gives the closest possible number of steps.
    #
    # Note that if pb_obj.dur precisely equals to half-integer number of steps,
    # resulting duration will be pb_obj.dur +/- step/2 and sign may vary randomly
    # (consequence of float-comparison uncertainty for nominally equal floats)

    # Number of points added to meet length constraints
    add_pts = 0

    # Sanity checks -----------------------------------------------------------

    # There is a default pulse for each of the channels in p_dict
    if not set(pb_obj.p_dict.keys()) <= set(pb_obj.dflt_dict.keys()):
        raise ValueError(
            'Every channel with non-default pulses must have the default pulse. \n'
            'The following channels contain non-default pulses: \n'
            '   {} \n'
            'The following channels have default pulse: \n'
            '   {}'
            ''.format(
                sorted(list(pb_obj.p_dict.keys())),
                sorted(list(pb_obj.dflt_dict.keys()))
            )
        )

    # Sample array length fits hardware constraints
    # - length step
    if n_pts % len_step != 0:
        if len_adj:
            new_n_pts = int(
                (n_pts // len_step + 1) * len_step
            )
            add_pts = new_n_pts - n_pts
            n_pts = new_n_pts
        else:
            raise ValueError(
                'Calculated number of points {} does not match hardware step {}. \n'
                'To enable auto-appending of default values, set len_adj to True'
                ''.format(n_pts, len_step)
            )
    # - min length
    if not len_min <= n_pts:
        if len_adj:
            add_pts = len_min - n_pts
            n_pts = len_min
        else:
            raise ValueError(
                'Calculated number of points {} is below hardware minimum {}. \n'
                'Try increasing sampling rate or pulse block duration'
                ''.format(n_pts, len_min)
            )
    # - max length
    if not n_pts <= len_max:
        raise ValueError(
            'Calculated number of points {} is above hardware maximum {}. \n'
            'Try decreasing sampling rate or pulse block duration'
            ''.format(n_pts, len_max)
        )

    # Sample pulse block ------------------------------------------------------

    # Generate arrays of T-points
    t_ar = np.linspace(
        start=0,
        stop=t_step * (n_pts - 1),
        num=n_pts
    )

    # Construct sample array for each channel in dflt_dict.keys()
    # and store it in samp_dict
    samp_dict = dict()

    for ch in pb_obj.dflt_dict.keys():

        # Fill the array with default values
        samp_dict[ch] = pb_obj.dflt_dict[ch].get_value(t_ar=t_ar)

        # Iterate through each pulse item and calculate
        # non-default values for corresponding T-points
        if ch in pb_obj.p_dict.keys():

            for p_item in pb_obj.p_dict[ch]:

                # find indexes of pulse edges
                indx_1 = int(p_item.t0 // t_step)
                indx_2 = int((p_item.t0 + p_item.dur) // t_step)

                # calculate new values
                val_ar = p_item.get_value(
                    t_ar=t_ar[indx_1 : indx_2+1]
                )

                # set the values to sample array
                samp_dict[ch][indx_1 : indx_2+1] = val_ar

    if debug:
        return samp_dict, n_pts, add_pts, t_ar
    else:
        return samp_dict, n_pts, add_pts
