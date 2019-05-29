import numpy as np


def pb_sample(pb_obj, samp_rate, len_min=0, len_max=float('inf'), len_step=1, step_adj=True, debug=False):

    t_step = 1 / samp_rate
    n_pts = int(pb_obj.dur//t_step + 1)
    add_pts = 0

    #
    # Sanity checks
    #

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
        if step_adj:
            new_n_pts = int(
                (n_pts // len_step + 1) * len_step
            )
            add_pts = new_n_pts - n_pts
            n_pts = new_n_pts
        else:
            raise ValueError(
                'Calculated number of points {} does not match hardware step {}. \n'
                'To enable auto-appending of default values, set step_adj to True'
                ''.format(n_pts, len_step)
            )
    # - min length
    if not len_min <= n_pts:
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

    #
    # Sample pulse block
    #

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
