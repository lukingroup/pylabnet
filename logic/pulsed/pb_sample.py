import numpy as np


def add_offset(pb_obj, offset_dict):
    pass


def chnl_map():
    pass


def pb_sample(pb_obj, samp_rate, len_min=0, len_max=float('inf'), len_step=1, step_adj=True):

    t_step = 1 / samp_rate
    n_pts = int(pb_obj.dur//t_step + 1)

    # Sanity checks
    # - length step
    if n_pts % len_step != 0:
        if step_adj:
            n_pts = int(
                (n_pts // len_step + 1) * len_step
            )
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

    # Generate arrays of T-points
    t_ar = np.linspace(
        start=0,
        stop=t_step * (n_pts - 1),
        num=n_pts
    )

    # Construct sample array for each channel in ch_set
    # and store it in samp_dict
    samp_dict = dict()

    for ch in pb_obj.ch_set:

        # Fill the array with default values
        samp_dict[ch] = pb_obj.dflt_dict[ch].get_value(t_ar=t_ar)

        # Iterate through each pulse item and calculate
        # non-default values for corresponding T-points
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

    return t_ar, samp_dict
