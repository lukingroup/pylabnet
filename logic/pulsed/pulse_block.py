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
        if cflct_er and ch in self.p_dict.keys():

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
        if ch not in self.p_dict.keys():
            self.p_dict[ch] = []

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

            for ch_ in self.p_dict.keys():
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
        if cflct_er and (set(self.p_dict.keys()) & set(pb_obj.p_dict.keys())):
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
            for ch in pb_obj.p_dict.keys():
                for p_item in pb_obj.p_dict[ch]:
                    p_item.t0 += t0
        else:
            for ch in self.p_dict.keys():
                for p_item in self.p_dict[ch]:
                    p_item.t0 += abs(t0)

        # Register new channels
        for ch in pb_obj.p_dict.keys():
            if ch not in self.p_dict.keys():
                self.p_dict[ch] = []

        # Add new pulses
        for ch in pb_obj.p_dict.keys():
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

    def ch_map(self, map_dict):

        #
        # Sanity check:
        #

        # - map_dict.keys() covers p_dict.keys()
        if not set(self.p_dict.keys()) <= set(map_dict.keys()):
            raise ValueError(
                'ch_map(): map_dict does not include all channels of p_dict: \n'
                '   map_dict.keys()={} \n'
                'self.p_dict.keys()={} \n'
                ''.format(
                    sorted(map_dict.keys()),
                    sorted(self.p_dict.keys())
                )
            )

        # - map_dict.keys() covers dflt_dict.keys()
        if not set(self.dflt_dict.keys()) <= set(map_dict.keys()):
            raise ValueError(
                'ch_map(): map_dict does not include all channels of dflt_dict \n'
                '      map_dict.keys() = {} \n'
                'self.dlft_dict.keys() = {}'
                ''.format(
                    sorted(map_dict.keys()),
                    sorted(self.dflt_dict.keys())
                )
            )

        #
        # Channel mapping
        #

        # Store references to the original pulse
        # dictionaries in temporary variables
        tmp_p_dict = self.p_dict
        tmp_dflt_dict = self.dflt_dict

        # Create empty dicts to store original
        # pulse lists / pulses with new channel names
        self.p_dict = dict()
        self.dflt_dict = dict()

        # Fill-in new p_dict with original pulse lists
        for ch in tmp_p_dict.keys():
            self.p_dict[map_dict[ch]] = tmp_p_dict[ch]

        # Fill-in new dflt_dict with original dflt pulses
        for ch in tmp_dflt_dict.keys():
            self.dflt_dict[map_dict[ch]] = tmp_dflt_dict[ch]

        del tmp_p_dict, tmp_dflt_dict

    def add_offset(self, offset_dict):
        pass

    def reset_edges(self):

        p_ch_list = list(self.p_dict.keys())

        # Left edge ==============

        # Find the left-most edge - it will be set to origin
        left_edge_list = [
            self.p_dict[ch][0].t0 for ch in p_ch_list
        ]
        left_edge = min(left_edge_list)

        # Shift all pulses such that the left-most edge
        # coincides with zero
        for ch in self.p_dict.keys():
            for p_item in self.p_dict[ch]:
                p_item.t0 -= left_edge

        # Right edge ==============

        # Find the right-most edge - the duration of the block
        right_edge_list = [
            self.p_dict[ch][-1].t0 + self.p_dict[ch][-1].dur for ch in p_ch_list
        ]
        self.dur = max(right_edge_list)
        # =

    def save(self):
        # TODO: implement
        pass

    @staticmethod
    def load():
        # TODO: implement
        pass

    def __str__(self):
        pulse_ch_list = sorted(list(self.p_dict.keys()))
        dflt_ch_list = sorted(list(self.dflt_dict.keys()))

        ret_str = 'PulseBlock "{}" \n' \
                  'pulse_chs = {} \n' \
                  'deflt_chs = {} \n' \
                  'dur = {:.2e} \n' \
                  'p_dict: \n' \
                  ''.format(self.name, pulse_ch_list, dflt_ch_list, self.dur)

        for ch in self.p_dict.keys():
            ch_str = '    {}: \n'.format(ch)
            for p_obj in self.p_dict[ch]:
                ch_str += '        {{{:.2e}, {:.2e}, {}}}\n'.format(p_obj.t0, p_obj.dur, str(p_obj))

            ret_str += ch_str
            ret_str += '\n'

        ret_str += 'dflt_dict: \n'
        for ch in self.dflt_dict.keys():
            ret_str += '    {}: {} \n'.format(ch, str(self.dflt_dict[ch]))

        return ret_str

