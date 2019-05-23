import numpy as np
import copy


class PulseBlock:
    def __init__(self, p_obj_list=None, dflt_dict=None, name=''):
        # p_obj_list = [
        #     po.High(chnl='ch1', t=0, dur=1e-6),
        #     po.Sin(chnl='ch2', t=1e-6, dur=1e-6, amp=1e-3, freq=2.5e9, ph=0)
        # ]

        # p_dict = {
        #     'ch1': [
        #         PulseObject(ch, t=0, dur, ...),
        #         PulseObject(ch, t=0, dur, ...),
        #         PulseObject(ch, t=0, dur, ...)
        #     ],
        #     'ch3': [
        #         PulseObject(ch, t=0, dur, ...),
        #         PulseObject(ch, t=0, dur, ...)
        #     ],
        #
        # }

        self.name = name
        self.ch_set = set()
        self.dur = 0
        self.p_dict = dict()
        self.dflt_dict = dict()

        if dflt_dict is not None:
            self.dflt_dict = copy.deepcopy(dflt_dict)

        if p_obj_list is None:
            p_obj_list = list()

        # Among given pulses, there may be several with negative offsets.
        #
        # If one just sequentially passes the them to insert(), it will shift
        # the T-origin. But the requested offsets for next pulses will not change,
        # thus next pulses will be place in unexpected shifted positions
        # (when passing several pulses at a time, the user thinks of the whole block
        # in a single frame and the offsets mean mutual position of pulses).
        #
        # To avoid this problem, below one checks all pulses, finds the largest
        # negative offset t_shift and just shifts all pulses by this amount before
        # calling insert(). In this case insert() does not perform any origin
        # shift.

        t_shift = 0
        for p_obj in p_obj_list:
            if p_obj.t0 < 0:
                t_shift = max(t_shift, abs(p_obj.t0))

        # Iterate through all given pulses and
        # insert them into the block
        for p_obj in p_obj_list:

            p_obj = copy.deepcopy(p_obj)
            p_obj.t0 += t_shift

            self.insert(p_obj=p_obj)

    def insert(self, p_obj, cflct_er=True):

        p_obj = copy.deepcopy(p_obj)
        ch = p_obj.ch

        # Sanity check: new pulse does not conflict with existing pulses
        if cflct_er and ch in self.ch_set:

            p_list = self.p_dict[ch]

            t0_list = np.array(
                [p_item.t0 for p_item in p_list]
            )
            idx = np.searchsorted(t0_list, p_obj.t0)

            if idx > 0:
                # Check for overlap with existing pulse to the left
                if not (p_list[idx-1].t0 + p_list[idx-1].dur) <= p_obj.t0:
                    raise ValueError(
                        'insert(): given pulse {} overlaps with existing pulse to the left'
                        ''.format(p_obj)
                    )

            if idx < len(p_list):
                # Check for overlap with existing pulse to the right
                if not (p_obj.t0 + p_obj.dur) <= p_list[idx].t0:
                    raise ValueError(
                        'insert(): given pulse {} overlaps with existing pulse to the right'
                        ''.format(p_obj)
                    )

        # Create a new entry for 'ch' if it is not yet registered
        if ch not in self.ch_set:
            self.p_dict[ch] = []
            self.ch_set.add(ch)

        # Add p_obj as a new entry in 'ch' pulse list
        self.p_dict[ch].append(p_obj)

        # T-order pulses within 'ch'
        self.p_dict[ch].sort(
            key=lambda p_item: p_item.t0
        )

        # Expand block edges if the new pulse sticks out:
        #   - beyond the end
        self.dur = max(self.dur, p_obj.t0 + p_obj.dur)
        #   - before the beginning
        if p_obj.t0 < 0:

            # shift every pulse to the right
            t_shift = abs(p_obj.t0)

            for ch_ in self.ch_set:
                for p_item in self.p_dict[ch_]:
                    p_item.t0 += t_shift

            # update duration
            self.dur += t_shift

    def join(self, p_obj, cflct_er=True, name=''):
        new_pb = copy.deepcopy(self)
        new_pb.name = name
        new_pb.insert(p_obj=p_obj, cflct_er=cflct_er)
        return new_pb
        # pass

    def insert_pb(self, pb_obj, t0=0, cflct_er=True):

        pb_obj = copy.deepcopy(pb_obj)

        # Sanity checks
        #  - no overlap between blocks
        if cflct_er and (self.ch_set & pb_obj.ch_set):
            if t0 >= 0:
                if not self.dur <= t0:
                    raise ValueError(
                        'insert_pb(): blocks overlap and cannot be merged. (DEBUG: t0 > 0)'
                    )
            else:
                if not pb_obj.dur <= abs(t0):
                    raise ValueError(
                        'insert_pb(): blocks overlap and cannot be merged. (DEBUG: t0 < 0)'
                    )
        #  - no conflicts between default pulse objects
        if cflct_er:
            for ch in pb_obj.dflt_dict.keys():
                if ch in self.dflt_dict.keys() and pb_obj.dflt_dict[ch] != self.dflt_dict[ch]:
                    raise ValueError(
                        'insert_pb(): conflict between default pulse objects on channel "{}"'
                        ''.format(ch)
                    )

        # Calculate duration
        if t0 >= 0:
            self.dur = max(self.dur, pb_obj.dur + t0)
        else:
            self.dur = max(abs(t0) + self.dur, pb_obj.dur)

        # Shift all elements of the right-most block
        if t0 >= 0:
            for ch in pb_obj.ch_set:
                for p_item in pb_obj.p_dict[ch]:
                    p_item.t0 += t0
        else:
            for ch in self.ch_set:
                for p_item in self.p_dict[ch]:
                    p_item.t0 += abs(t0)

        # Register new channels
        for ch in pb_obj.ch_set:
            if ch not in self.ch_set:
                self.ch_set.add(ch)
                self.p_dict[ch] = []

        # Add new pulses
        for ch in pb_obj.ch_set:
            self.p_dict[ch].extend(
                pb_obj.p_dict[ch]
            )

            if t0 < 0:
                # Pulses from pb_obj were added from the right
                # Sort pulses in T-order to move them to the left
                self.p_dict[ch].sort(
                    key=lambda pulse_item: pulse_item.t0
                )

        # Add new default pulse objects
        for ch in pb_obj.dflt_dict.keys():
            if ch not in self.dflt_dict.keys():
                self.dflt_dict[ch] = copy.deepcopy(
                    pb_obj.dflt_dict[ch]
                )
        # pass

    def join_pb(self, pb_obj, t0=0, cflct_er=True, name=''):
        new_pb = copy.deepcopy(self)
        new_pb.name = name
        new_pb.insert_pb(
            pb_obj=pb_obj,
            t0=t0,
            cflct_er=cflct_er
        )
        return new_pb
        # pass

    def save(self):
        # TODO: implement
        pass

    @staticmethod
    def load():
        # TODO: implement
        pass

    def __str__(self):
        ret_str = 'PulseBlock "{}" \n' \
                  'ch_set = {} \n' \
                  'dur = {:.2e} \n' \
                  'p_dict: \n' \
                  ''.format(self.name, self.ch_set, self.dur)

        # TODO: each p_item on a new line
        for ch in self.ch_set:
            ch_str = '    {}: \n'.format(ch)
            for p_obj in self.p_dict[ch]:
                ch_str += '        {{{:.2e}, {:.2e}, {}}}\n'.format(p_obj.t0, p_obj.dur, str(p_obj))

            ret_str += ch_str
            ret_str += '\n'

        ret_str += 'dflt_dict: \n'
        for ch in self.dflt_dict.keys():
            ret_str += '    {}: {} \n'.format(ch, str(self.dflt_dict[ch]))

        return ret_str

