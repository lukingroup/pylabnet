import numpy as np


def sample_pb(pb_obj, samp_rate, len_min=0, len_max=float('inf'), len_step=1, step_adj=True):

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

    t_ar = np.linspace(
        start=0,
        stop=t_step * (n_pts - 1),
        num=n_pts
    )

    samp_dict = dict()
    for ch in pb_obj.ch_set:

        # Determine type of return values
        # of pulse objects on this channel.
        #
        # Assumptions:
        # - if 'ch' key is present in p_dict, corresponding list is non-empty
        # - all p-elements of a channel have the same return type
        # - all Pulse classes used have ret_type property

        ret_type = pb_obj.p_dict[ch][0].ret_type

        #
        if ret_type == np.float32:
        samp_dict[ch] = np.zeros(n_pts)

        for p_item in pb_obj.p_dict[ch]:
            pass

    return None


def add_offset(pb_obj, offset_dict):
    pass
