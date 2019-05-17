from utils.helper_methods import str_to_float
import numpy as np
import copy


class PulseBlock:
    def __init__(self, *pulse_items, name=''):
        # pulse_items = [
        #     dict(chnl='ch1', t=0, p_obj=pulse.High()),
        #     dict(chnl='ch2', t='1 us', p_obj=pulse.Sin(...))
        # ]

        # pulse_dict = {
        #     'ch1': [
        #         dict(t=0, p_obj=pulse.High()),
        #         dict(t='1 us', p_obj=pulse.Sin(...))
        #     ],
        #     'ch3': [
        #         dict(t=0, p_obj=pulse.High()),
        #         dict(t='1 us', p_obj=pulse.Sin(...))
        #     ],
        #
        # }

        self.name = name
        self.pulse_dict = dict()
        self.chnl_set = set()
        self.dur = 0

        # Among given pulses, there may be several with negative offsets.
        #
        # If one just sequentially passes the them to add_pulse(), it will shift
        # the T-origin. But the requested offsets for next pulses will not change,
        # thus next pulses will be place in unexpected shifted positions
        # (when passing several pulses at a time, the user thinks of the whole block
        # in a single frame and the offsets mean mutual position of pulses).
        #
        # To avoid this problem, below one checks all pulses, finds the largest
        # negative offset t_shift and just shifts all pulses by this amount before
        # calling add_pulse(). In this case add_pulse() does not perform any origin
        # shift.

        t_shift = 0
        for arg_dict in pulse_items:
            if 't' in arg_dict.keys():
                t = str_to_float(arg_dict['t'])
                if t < 0:
                    t_shift = max(t_shift, abs(t))

        # Iterate through all given pulses and
        # add them to the block
        for arg_dict in pulse_items:
            chnl = arg_dict['chnl']
            p_obj = arg_dict['p_obj']
            if 't' in arg_dict.keys():
                t = str_to_float(arg_dict['t'])
            else:
                t = 0

            self.add_pulse(
                chnl=chnl,
                t=t + t_shift,
                p_obj=p_obj
            )

    def add_pulse(self, p_obj, chnl, t=0):

        t = str_to_float(t)

        # Create a new entry for 'chnl' if it is not yet registered
        if chnl not in self.chnl_set:
            self.pulse_dict[chnl] = []
            self.chnl_set.add(chnl)

        # Add pulse_obj as a new entry in 'chnl' pulse list
        self.pulse_dict[chnl].append(
            dict(t=t, p_obj=p_obj)
        )

        # T-order pulses within 'chnl'
        self.pulse_dict[chnl].sort(
            key=lambda item_dict: item_dict['t']
        )

        # Expand block edges if the new pulse sticks out:
        #   - beyond the end
        self.dur = max(self.dur, t + p_obj.dur)
        #   - before the beginning
        if t < 0:
            # shift every pulse to the right
            for chnl_ in self.chnl_set:
                for pulse_item_dict in self.pulse_dict[chnl_]:
                    pulse_item_dict['t'] += abs(t)
            # update duration
            self.dur += abs(t)

    def save(self):
        # TODO: implement
        pass

    @staticmethod
    def load():
        # TODO: implement
        pass

    def __str__(self):
        ret_str = 'PulseBlock "{}" \n' \
                  'chnl_set = {} \n' \
                  'dur = {:.2e} \n' \
                  'pulse_dict: \n' \
                  ''.format(self.name, self.chnl_set, self.dur, self.pulse_dict)

        for chnl in self.pulse_dict.keys():
            p_item_list = '    {}: '.format(chnl)
            for p_item in self.pulse_dict[chnl]:
                p_item_list += '{{{:.2e}, {}}}  '.format(p_item['t'], str(p_item['p_obj']))

            ret_str += p_item_list
            ret_str += '\n'

        return ret_str

    def iplot(self):
        # TODO: implement
        pass


def merge(*pb_items, name=''):

    # Handle three different types of input:
    #
    # 1) just PulseBlock - the block to be added without t-offset
    #
    # 2) tuple(PulseBlock_instance, offset) - the block to be added
    # with t-offset
    #
    # 3) dict('p_obj'=Pulse_instance, 'chnl'='chnl_name', 't'=offset)
    # a single pulse to be wrapped into a PulseBlock and added with
    # offset.
    #
    # Analyze each arg_item and sore result in pb_dict_list.

    pb_dict_list = []

    for arg_item in pb_items:
        # 1) just PulseBlock - block without t-offset
        if isinstance(arg_item, PulseBlock):

            pb_dict_list.append(
                dict(
                    pb_obj=arg_item,
                    offset=0
                )
            )

        # 2) tuple(PulseBlock_instance, offset)
        elif isinstance(arg_item, tuple):

            # Check that PulseBlock is given first
            if not isinstance(arg_item[0], PulseBlock):
                raise ValueError(
                    'merge(): wrong parameter order in {}.\n'
                    'To specify offset, pass a tuple (PulseBlock, offset)'
                    ''.format(arg_item)
                )

            pb_dict_list.append(
                dict(
                    pb_obj=arg_item[0],
                    offset=str_to_float(arg_item[1])
                )
            )

        # 3) dict('p_obj'=Pulse_instance, 'chnl'='chnl_name', 't'=offset)
        # a single pulse to be wrapped into a PulseBlock
        elif isinstance(arg_item, dict):

            # Note: single-pulsed PulseBlock effectively ignores negative
            # offset arg_item['t'].
            # That is why one has to extract offset and apply it manually.
            if 't' in arg_item.keys():
                temp_t = arg_item['t']
                temp_ar_item = copy.deepcopy(arg_item)
                temp_ar_item['t'] = 0
            else:
                temp_t = 0
                temp_ar_item = arg_item

            pb_dict_list.append(
                dict(
                    pb_obj=PulseBlock(temp_ar_item),
                    offset=temp_t
                )
            )

        # Unknown type of argument
        else:
            raise ValueError(
                'merge(): invalid argument {} was passed \n'
                'Arguments can be only be PulseBlock, tuple(PulseBlock, offset), '
                'or dict("chnl"=channel_name, "t"=offset, "p_obj"=pulse_object).'
                ''.format(arg_item)
            )

    # Find the largest negative offset t_shift
    # to shift all blocks before calling _merge()
    t_shift = 0
    for pb_dict in pb_dict_list:
        if pb_dict['offset'] < 0:
            t_shift = max(
                t_shift,
                abs(pb_dict['offset'])
            )

    # Create blank of the new PulseBlock, which will be returned
    new_pb = PulseBlock()

    # Add all given pulse blocks
    # (shifted offset is expected to be non-negative for each one)
    for pb_dict in pb_dict_list:
        new_pb = _merge(
            pb1=new_pb,
            pb2=pb_dict['pb_obj'],
            offset=t_shift + pb_dict['offset']
        )

    new_pb.name = name
    return new_pb
    # pass


def _merge(pb1, pb2, offset=0, name=''):

    offset = str_to_float(offset)

    # Create copies of both pulse blocks
    # to avoid modifying passed instances
    pb1 = copy.deepcopy(pb1)
    pb2 = copy.deepcopy(pb2)

    # Sanity checks
    #   - non-negative offset is expected
    if offset < 0:
        raise ValueError(
            '_merge(): only positive offset is allowed for this low-level method. \n'
            'Use merge() for more generic types of input'
        )

    #   - if there is channel overlap, there can be no temporal overlap
    if pb1.chnl_set & pb2.chnl_set:
        if offset < pb1.dur:
            raise ValueError(
                '_merge(): pulse blocks with both channel and temporal overlap cannot be merged: '
                'there are conflicting bins for common channels'
            )

    # Create a blank of the new pulse block
    # which will be returned
    new_pb = PulseBlock(name=name)

    # Register all channels
    new_pb.chnl_set = pb1.chnl_set | pb2.chnl_set
    for chnl in new_pb.chnl_set:
        new_pb.pulse_dict[chnl] = []

    # Calculate duration
    new_pb.dur = max(pb1.dur, offset + pb2.dur)

    # Shift all pulses in pb2 by offset
    for chnl in pb2.chnl_set:
        for pulse_dict_item in pb2.pulse_dict[chnl]:
            pulse_dict_item['t'] += offset

    # Fill-in new_pb.pulse_dict
    #   Since pulse items are T-ordered in pb1 an pb2
    #   and pb2 goes after pb1 (or there is no channel overlap),
    #   for every chanel one can simply add all pulses from pb1
    #   and then add all pulses from pb2.

    for chnl in pb1.chnl_set:
        new_pb.pulse_dict[chnl].extend(
            pb1.pulse_dict[chnl]
        )

    for chnl in pb2.chnl_set:
        new_pb.pulse_dict[chnl].extend(
            pb2.pulse_dict[chnl]
        )

    return new_pb
