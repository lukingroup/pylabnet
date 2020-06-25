import pulseblock.pulse_block as pb
import numpy as np
import copy


def pb_zip(pb_obj, dur_quant):
    """ Collapse default (wait) periods into repetitions of a single wait block.

    This method takes a plain PulseBlock and returns a sequence table and a list
    of individual waveforms (snippets).
    Corresponding pulse sequence reproduces the original waveform but with long
    wait periods replaced by multiple repetitions of the same short wait element
    for saving hardware memory (collapsing or zipping of a waveform).

    :param pb_obj: PulseObject instance - original pulse block to be collapsed

    :param dur_quant: (float) minimal waveform duration allowed by the hardware
    memory (in the same units as used in pb_obj).
    This value is normally determined as
        min_wfm_size / sampling_rate,
    where min_wfm_size is the minimal size of a sample array in hardware memory.
    The repeated wait waveform will have this size.

    :return: (dict)
    {
        'seq_list': list of tuples ('wfm_name', repetition_number) - chronological
        sequence of (name of the wfm snippet, how many times it should be repeated)

        'snip_list': list of PulseBlock objects - 'snippets' of the original pb_obj,
        which form the sequence according to seq_list
        Naming convention:
            pb_obj.name + '_wait' for the repeated wait wfm
            pb_obj.name + '_' + 'snip number {0, 1, ...}' for non-repeated snippets
        Order: wait is the first element, non-repeated snippets go next in
            chronological order.
    }
    """

    # Non-default intervals ---------------------------------------------------

    # find all time intervals covered by non-default pulses
    p_interval_list = []
    for ch in pb_obj.p_dict.keys():
        for pulse in pb_obj.p_dict[ch]:
            p_interval_list.append(
                (pulse.t0, pulse.t0 + pulse.dur)
            )

    # merge all overlapping pulse intervals
    p_interval_list = merge_intervals(i_list=p_interval_list)

    # Step usage dictionary ---------------------------------------------------

    # Now one knows all the wait periods witch can be collapsed
    # (full duration of pb_obj minus all pulse intervals)
    #
    # But both the wait waveform and non-trivial pulse waveforms have to
    # meet the length constraint: dur_quant + n*dur_step. That is why it is
    # not trivial to split full duration into repetitions of wait element and
    # non-default waveforms.
    #
    # Here one uses the easiest (perhaps not the most efficient) way to meet
    # these restrictions:
    # - divide the entire duration of pb_obj into discrete steps of dur_quant
    # - construct dur_quant-long wait waveform
    # - if a given step does not contain any pulses (or any parts of pulses),
    # it will be replaced by a repetiotion of wait wfm
    # - if one or several adjacent steps contain non-default pulses, they are
    # merged and output as a single pulse block
    # - last integer dur_quant is merged with the reminder (shorter than dur_quant)
    # and is returned as a single pulse block (because the reminder is shorter
    # than minimal waveform length and cannot be sampled alone)

    # Number of whole dur_quant, fitting into pb_obj.dur
    quant_num = int(pb_obj.dur // dur_quant)

    # Use array:
    #   False - this dur_quant is a wait period
    #   True - this dur_quant is a part of pulse interval
    use_ar = np.full(
        shape=quant_num,
        fill_value=False
    )

    # Determine which steps contain non-default pulses
    for p_interval in p_interval_list:
        left_idx = int(p_interval[0] // dur_quant)
        right_idx = int(p_interval[1] // dur_quant)

        # Handle left-most interval
        #   If p_interval[0] == 0.0, integer division by dur_quant
        #   may accidentally evaluate to -1.0
        if left_idx < 0:
            left_idx = 0

        # Handle right-most intervals
        if left_idx == quant_num-1 or left_idx == quant_num:
            # The entire interval fits into the 'default-True' area
            # [(quant_num - 1)-st element and reminder], so no change
            # has to be made in use_ar
            continue
        elif right_idx == quant_num:
            # The left edge of the interval is outside of the 'default-True'
            # area [(quant_num - 1)-st elem and reminder], but the right edge
            # is in the reminder. The pulse might introduce non-trivial change
            # into use_ar, but right_idx is currently out of range.
            #
            # Reduce it to the max available index to avoid out-of-range and
            # broadcasting errors:
            right_idx = quant_num - 1

        use_ar[left_idx : right_idx+1] = np.full(
            shape=right_idx - left_idx + 1,
            fill_value=True
        )
    # Last integer step of dur_quant must be considered as non-wait
    # (to be merged and sampled with the reminder, which is shorter
    # than the hardware minimum)
    use_ar[-1] = True

    # Find periods of pulses / repeating wait (perform 'run-length encoding'):

    # The return is a period dictionary:
    # {
    #   'val_ar': True or False - this run of steps is non-default or wait
    #   'len_ar': number of dur_quant steps within each run
    #   'start_ar': starting index of each run
    # }
    period_dict = run_len_encode(in_ar=use_ar)

    # Final sequence table and PulseBlock dictionary --------------------------

    final_snip_list = []
    final_seq_list = []

    # Construct 'wait' PulseBlock
    wait_pb_name = pb_obj.name + '_wait'
    wait_pb = pb.PulseBlock(name=wait_pb_name)
    wait_pb.dur = dur_quant
    wait_pb.dflt_dict = copy.deepcopy(pb_obj.dflt_dict)
    final_snip_list.append(wait_pb)

    # Iterate through all pulse runs, take 'snippet pulse blocks',
    # and construct sequence table

    # The last run (must be non-wait) will be extended to include the reminder
    last_period_idx = len(period_dict['val_ar']) - 1
    # This counter is used to keep track of PulseBlock names
    pb_name_idx = 0

    for period_idx, period_val in enumerate(period_dict['val_ar']):

        # Pulse period
        if period_val:

            # Take a snippet of this pulse period
            tmp_pb_name = pb_obj.name + '_{}'.format(pb_name_idx)

            # Snippet edges
            start_t = period_dict['start_ar'][period_idx] * dur_quant
            if period_idx < last_period_idx:
                # pulse period in the bulk - take the snippet by the period edges
                stop_t = (period_dict['start_ar'][period_idx] +
                          period_dict['len_ar'][period_idx]) * dur_quant
            else:
                # right-most pulse period must be extended to include the reminder
                stop_t = pb_obj.dur

            tmp_pb = pb_snip(
                pb_obj=pb_obj,
                start_t=start_t,
                stop_t=stop_t,
                snip_name=tmp_pb_name,
                use_centers=True
            )

            # Add the snippet to the PulseBlock list
            final_snip_list.append(tmp_pb)
            # Add corresponding entry to the sequence table:
            #   output tmp_pb_name once
            final_seq_list.append(
                (tmp_pb_name, 1)
            )
            # Increment name index for the next PulseBlock
            pb_name_idx += 1

        # Wait period
        else:
            # Only add an entry to the sequence table:
            #   output 'wait waveform n times'
            final_seq_list.append(
                (wait_pb_name, period_dict['len_ar'][period_idx])
            )

    return {
        'seq_list': final_seq_list,
        'snip_list': final_snip_list
    }


def pb_expand_test(res_dict, indicate_bounds=True):
    """ Helper method to test pb_zip()

    This method takes direct output res_dict of pb_zip() call and reconstructs
    the original pulse block according to the sequence.
    To visualize boundaries between individual sequence elements, set optional
    indicate_bounds parameter to True. This will add zero-length divider pulses
    on one of the channels.

    :param res_dict: (dict) return of pb_zip() call to be reconstructed back
    into a plain waveform.
    :param indicate_bounds: (bool) if True, divider pulses will be added to one
    of the channels after each individual waveform.
    :return: (PulseBlock) reconstructed plain waveform
    """

    import pulseblock.pulse as po

    new_pb = pb.PulseBlock()

    seq_list = res_dict['seq_list']
    snip_list = res_dict['snip_list']

    for snip_idx in range(len(seq_list)):
        snip_name, rep_num = seq_list[snip_idx]

        for rep_idx in range(rep_num):

            # Find wfm_snip corresponding to snip_name
            wfm_snip = None
            for wfm_snip in snip_list:
                if wfm_snip.name == snip_name:
                    break

            new_pb.append_pb(
                pb_obj=wfm_snip
            )

            # Add a marker to indicate the block boundary
            if indicate_bounds:
                mrk_ch = list(
                    wfm_snip.dflt_dict.keys()
                )[0]

                new_pb.append(
                    p_obj=po.PTrue(
                        ch=mrk_ch,
                        dur=0
                    ),
                    cflct_er=False
                )

    return new_pb


# Technical methods


def merge_intervals(i_list):
    """ Merge overlapping intervals from a (un-ordered) list

    Each interval should be represented by a tuple
        (interval_beginning_val, interval_end_val )

    :param i_list: list of tuples - original intervals

    :return: list of tuples - list of merged intervals.
    These intervals do not overlap and are sorted in ascending order.
    """

    sorted_i_list = sorted(i_list, key=lambda i_tup: i_tup[0])
    merged_i_list = []

    for idx in range(len(sorted_i_list)):

        # In the very begining, just add the left-most interval
        # to merged_i_list
        if idx == 0:
            merged_i_list.append(sorted_i_list[0])

        else:
            # Pop-out the right-most element from merged_i_list
            # [pop-outing is necessary because the interval
            # will be changed (extended) if merging is performed]
            left_i_tup = merged_i_list.pop()

            # Check for overlap with the next interval to the right from
            # sorted_i_list
            right_i_tup = sorted_i_list[idx]

            if left_i_tup[1] >= right_i_tup[0]:
                # The two intervals overlap:
                #   merge them and append the extended interval to merged_i_list
                new_tup = tuple(
                    [
                        left_i_tup[0],
                        max(left_i_tup[1], right_i_tup[1])
                    ]
                )
                merged_i_list.append(new_tup)

            else:
                # The two intervals do not overlap:
                #   return left_i_tup to its' original place in the merged_i_list and
                #   append right_i_tup - the new right-most interval to be checked for
                #   overlap with subsequent intervals from sorted_i_list
                merged_i_list.append(left_i_tup)
                merged_i_list.append(right_i_tup)

    return merged_i_list


def run_len_encode(in_ar):
    """ Run-length encode the input array:
    finds runs of identical values and replaces them with
    {run start index, run length, run value}.

    :param in_ar: input array
    :return: (dict)
        {
            'start_ar': run start indices [np.array(np.int)]
            'len_ar': run lengths [np.array(np.int)]
            'val_ar': values within each run [np.array(dtype of in_ar)]
        }
    """

    ar_len = len(in_ar)
    in_ar = np.asarray(in_ar)

    if ar_len == 0:
        return {
            'start_ar': np.array([]),
            'len_ar': np.array([]),
            'val_ar': np.array([])
        }

    # Run starting indices
    # - pairwise comparison:
    #   check whether the next element coincides with current
    pairwise_comp = in_ar[1:] != in_ar[:-1]

    # - run start indices
    start_ar = np.concatenate((
        [0],  # the first element is always a beginning of a run
        np.where(pairwise_comp)[0] + 1  # beginnings of all subsequent runs
    ))
    # [0] is needed because np.where() returns a tuple of arrays for each dimension
    # +1 is needed because pairwise_comp contains indices of elements to the left
    # from the run boundaries, whereas starting points are the ones to the right

    # Run lengths
    len_ar = np.diff(start_ar)
    # append length of the right-most run
    len_ar = np.append(
        len_ar,
        ar_len - start_ar[-1]
    )

    # Values within each run
    val_ar = np.take(
        a=in_ar,
        indices=start_ar
    )

    return {
        'start_ar': start_ar,
        'len_ar': len_ar,
        'val_ar': val_ar
    }


def pb_snip(pb_obj, start_t, stop_t, snip_name=None, use_centers=False):
    """ PulseBlock snipping tool

    Copies all default values and all pulse objects between the snippet edges
    with preserved order and spacing between them.
    The start_t and stop_t edges are the origin and the end of the returned
    PulseBlock object.

    Note that snippet edge must not cross any pulse object (but can touch it).
    If any edge crosses any pulse object, ValueError exception is produced.

    Assumptions:
    - pulse objects are ascending-time-ordered within pb_obj.p_dict[ch_name]
    - all pulse objects have non-zero duration. The algorithm will still work
     for a zero-duration pulse, but it might be ether left out or included
     into the snippet unpredictably, if it touches the edges star_t or stop_t.

    :param pb_obj: original PulseBlock
    :param start_t: (float) left snippet edge
    :param stop_t: (float) right snippet edge
    :param snip_name: (str, optional) name for the new PulseBlock object
                      If not given, pb_obj.name + '_snip' is used.
    :param use_centers: (bool) if False, belonging of a pulse to the snippet
    is determined by edges. If True - by position of the pulse central point

    :return: new PulseBlock object -
             snippet of pb_obj between start_t and stop_t
             Exception is produced in the case of error.
    """

    # New PulseBlock to be filled and returned
    new_pb = pb.PulseBlock()
    new_pb.dur = stop_t - start_t
    if snip_name is not None:
        new_pb.name = snip_name
    else:
        new_pb.name = pb_obj.name + '_snip'

    # Copy all default pulses
    new_pb.dflt_dict = copy.deepcopy(pb_obj.dflt_dict)

    # Copy all pulses falling in between start_t and stop_t
    for ch in pb_obj.p_dict.keys():
        for pulse in pb_obj.p_dict[ch]:

            # Assumption: pulses in pb_obj.p_dict[ch] are time-ordered
            # Assumption: all pulses have dur > 0.
            #   The algorithm will also work for a pulse of dur = 0,
            #   but such pulse might be left out or included unpredictably,
            #   if it touches the window edges star_t or stop_t.

            # Two ways to determine belonging of a block to the snippet:
            #
            # 1) whether the center of a pulse falls into [start_t, stop_t]
            # interval.
            #   Pros: robust against float-comparison errors if the pulse
            #     touches snippet edge.
            #   Cons: This method does not detect the cases when snippet
            #     edges go across a pulse block.
            #
            # 2) whether both edges of a pulse fall into [start_t, stop_t]
            #   Pros: checks for snippet edges crossing the pulse
            #   Cons: may unpredictably produce exceptions if one of the pulses
            #       touches snippet edge (due to unpredictable comparison result
            #       for two nominally identical floats)

            # Method 1: use pulse center
            if use_centers:
                pulse_center = pulse.t0 + pulse.dur/2
                if pulse_center <= start_t:
                    # pulse is fully to the left from snip window
                    continue

                elif start_t <= pulse_center <= stop_t:
                    # pulse is fully inside the snip window

                    if ch not in new_pb.p_dict.keys():
                        # the first time the pulse is added to this channel
                        new_pb.p_dict[ch] = []

                    pulse_copy = copy.deepcopy(pulse)
                    pulse_copy.t0 -= start_t
                    new_pb.p_dict[ch].append(pulse_copy)

                else:
                    # This pulse and all subsequent ones lie to the right
                    # from the snip window
                    break

            # Method 2: use pulse edges
            else:
                if pulse.t0+pulse.dur <= start_t:
                    # pulse is fully to the left from snip window
                    continue

                elif start_t <= pulse.t0 and pulse.t0+pulse.dur <= stop_t:
                    # pulse is fully inside the snip window

                    if ch not in new_pb.p_dict.keys():
                        # the first time the pulse is added to this channel
                        new_pb.p_dict[ch] = []

                    pulse_copy = copy.deepcopy(pulse)
                    pulse_copy.t0 -= start_t
                    new_pb.p_dict[ch].append(pulse_copy)

                elif stop_t <= pulse.t0:
                    # This pulse and all subsequent ones lie to the right
                    # from the snip window
                    break

                # The window edge goes across one of the pulse objects.
                # Since it is not clear what to do with such a pulse,
                # one has to raise an exception.
                # Alternatively, it might be some unexpected comparison error.
                else:
                    # Determine the conflicting edge
                    if pulse.t0 < start_t < pulse.t0+pulse.dur:
                        edge_type = 'start_t'
                        edge_t = start_t

                    elif pulse.t0 < stop_t < pulse.t0+pulse.dur:
                        edge_type = 'stop_t'
                        edge_t = stop_t

                    # Something completely unexpected:
                    # if it were just a crossing with an edge,
                    # one of the above conditions should have been satisfied.
                    # Hence, this part is reached only in the case of some
                    # unexpected error.
                    #
                    # Just raise an exception and provide all the information
                    else:
                        raise ValueError(
                            'pb_snip(): condition check failed: \n'
                            '   pulse_obj = {} \n'
                            '   t0 = {} \n'
                            '   dur = {} \n'
                            '   start_t = {} \n'
                            '   stop_t = {}'
                            ''.format(
                                pulse,
                                pulse.t0,
                                pulse.dur,
                                start_t,
                                stop_t
                            )
                        )

                    raise ValueError(
                        'pb_snip(): snip edge goes across a pulse object \n'
                        '   channel = {} \n'
                        '   t0 = {} \n'
                        '   t0+dur = {} \n'
                        '   pulse object = {} \n'
                        '   conflicting edge = {} \n'
                        '   edge position = {}'
                        ''.format(
                            ch,
                            pulse.t0,
                            pulse.t0 + pulse.dur,
                            str(pulse),
                            edge_type,
                            edge_t
                        )
                    )

    return new_pb
