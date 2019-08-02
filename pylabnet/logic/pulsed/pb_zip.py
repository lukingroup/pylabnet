import pylabnet.logic.pulsed.pulse_block as pb
import numpy as np
import copy


def pb_zip(pb_obj, dur_quant):

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
    # (to be merged and sampled with the reminder)
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

    final_pb_dict = dict()
    final_seq_list = []

    # Construct 'wait' PulseBlock
    wait_pb_name = pb_obj.name + '_wait'
    wait_pb = pb.PulseBlock(name=wait_pb_name)
    wait_pb.dur = dur_quant
    wait_pb.dflt_dict = copy.deepcopy(pb_obj.dflt_dict)
    final_pb_dict[wait_pb_name] = wait_pb

    # Iterate through all pulse runs, take 'snippet pulse blocks',
    # and construct sequence table

    # The last run (must be non-wait) will be extended to include the reminder
    last_period_idx = len(period_dict['val_ar']) - 1
    # This counter is used to keep track of PulseBlock names
    pb_name_idx = 0

    for period_idx, period_val in enumerate(period_dict['val_ar']):

        # Pulse period
        if period_val:
            tmp_pb_name = pb_obj.name + '_{}'.format(pb_name_idx)

            # pulse period in the bulk - take the snippet by the period edges
            if period_idx < last_period_idx:

                # Take a snippet of this pulse period
                start_t = period_dict['start_ar'][period_idx] * dur_quant
                stop_t = (period_dict['start_ar'][period_idx] +
                          period_dict['len_ar'][period_idx]) * dur_quant

                tmp_pb = pb_snip(
                    pb_obj=pb_obj,
                    start_t=start_t,
                    stop_t=stop_t,
                    snip_name=tmp_pb_name
                )

            # right-most pulse period must be extended to include the reminder
            else:
                start_t = period_dict['start_ar'][period_idx] * dur_quant
                stop_t = pb_obj.dur

                tmp_pb = pb_snip(
                    pb_obj=pb_obj,
                    start_t=start_t,
                    stop_t=stop_t,
                    snip_name=tmp_pb_name
                )

            # Add the snippet to the PulseBlock dictionary
            final_pb_dict[tmp_pb_name] = tmp_pb
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
        'pb_dict': final_pb_dict
    }
    # final_pb_list = []
    # final_wait_rep_list = []
    #
    # # Wait pulse block --------------------------------------------------------
    #
    # # Create elementary "wait" pulse block
    # wait_pb = pb.PulseBlock(name=pb_obj.name + '_wait')
    # wait_pb.dur = dur_quant
    #
    # # Copy all default pulses from pb_obj
    # for ch in pb_obj.dflt_dict.keys():
    #     wait_pb.dflt_dict[ch] = copy.deepcopy(
    #         pb_obj.dflt_dict[ch]
    #     )
    #
    # # Add wait block to the return list
    # final_pb_list.append(wait_pb)
    #
    # # Find non-wait intervals -------------------------------------------------
    # blk_list = []
    # for ch in pb_obj.p_dict.keys():
    #     for p_obj in pb_obj.p_dict[ch]:
    #         blk_list.append(
    #             (p_obj.t0, p_obj.t0 + p_obj.dur)
    #         )
    #
    # # Merge all overlapping intervals
    # blk_list = merge_intervals(i_list=blk_list)
    #
    # # Construct non-wait blocks -----------------------------------------------
    #
    # # --|**blk_idx=0**|--------|**blk_idx=1**|-----|**blk_idx=2**|-------|**blk_idx=n**|--
    #
    # for blk_idx in range(len(blk_list)):
    #     # Calculate integer-quant-matched time edges of this interval
    #     start_t = (blk_list[blk_idx][0] // dur_quant) * dur_quant
    #     stop_t = (blk_list[blk_idx][1] // dur_quant + 1) * dur_quant
    #
    #     # Create new pulse block with name = 'pb_obj_name + blk_idx'
    #     tmp_pb = pb.PulseBlock(name=pb_obj.name + '_{}'.format(blk_idx))
    #     tmp_pb.dur = stop_t - start_t
    #
    #     # Copy all default pulses
    #     for ch in pb_obj.dflt_dict.keys():
    #         tmp_pb.dflt_dict[ch] = copy.deepcopy(
    #             pb_obj.dflt_dict[ch]
    #         )
    #
    #     # Copy all covered non-default pulse objects
    #     for ch in pb_obj.p_dict.keys():
    #
    #         # Iterate through all pulse objects of this channel and
    #         # find the ones, which fall into [start_t, stop_t)
    #         for p_obj in pb_obj.p_dict[ch]:
    #
    #             if p_obj.t0 < start_t:
    #                 # Didn't reach the beginning of the interval yet
    #                 continue
    #
    #             elif p_obj.t0 < stop_t:
    #                 # This pulse object is covered by current time-interval
    #                 # Copy pulse and change offset (move origin to start_t)
    #                 p_obj_copy = copy.deepcopy(p_obj)
    #                 p_obj_copy.t0 -= start_t
    #                 # Insert pulse into new pulse block
    #                 tmp_pb.insert(
    #                     p_obj=p_obj_copy,
    #                     reset_edges=False
    #                 )
    #             else:
    #                 # All subsequent pulse objects of this channel
    #                 # are beyond the scope of current time interval
    #                 break
    #
    #     # Add the new pulse block to the final list
    #     final_pb_list.append(tmp_pb)
    #
    # # Calculate wait repetition numbers ----------
    # #   - determine the number of wait reps to the previous interval
    # # Wait before the first non-trivial interval
    # final_wait_rep_list.append(int(
    #     blk_list[0][0] // dur_quant
    # ))
    #
    # for blk_idx in range(1, len(blk_list)):
    #     final_wait_rep_list.append(int(
    #         (
    #                 blk_list[blk_idx][0] - blk_list[blk_idx - 1][1]
    #         ) // dur_quant
    #     ))


def pb_expand_test(res_dict):
    import pylabnet.logic.pulsed.pulse as po

    new_pb = pb.PulseBlock()

    seq_list = res_dict['seq_list']
    pb_dict = res_dict['pb_dict']

    for pb_name, rep_num in seq_list:
        for rep_idx in range(rep_num):
            new_pb.append_pb(
                pb_obj=pb_dict[pb_name]
            )

            mrk_ch = list(
                pb_dict[pb_name].dflt_dict.keys()
            )[0]

            new_pb.append(
                p_obj=po.PTrue(
                    ch=mrk_ch,
                    dur=0
                )
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


def merge_domains(tile_list):
    pass


def run_len_encode(in_ar):
    """ Run-length encode the input array:
    find runs oi identical values and replace them with
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


def pb_snip(pb_obj, start_t, stop_t, snip_name=None):
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

            else:
                # The window edge goes across one of the pulse objects.
                # Since it is not clear what to do with such a pulse,
                # one has to raise an exception.
                #
                # Alternatively, some unexpected comparison error occurred.

                # Determine the conflicting edge
                if pulse.t0 < start_t < pulse.t0+pulse.dur:
                    edge_type = 'start_t'
                    edge_t = start_t
                elif pulse.t0 < stop_t < pulse.t0+pulse.dur:
                    edge_type = 'stop_t'
                    edge_t = stop_t
                else:
                    # Something completely unexpected:
                    # if it were just a crossing with an edge,
                    # one of the above conditions should have been satisfied.
                    # Hence, this part is reached only in the case of some
                    # unexpected error.
                    #
                    # Just raise an exception and provide all the information
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



