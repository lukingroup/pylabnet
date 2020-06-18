import numpy as np
import copy


class PulseBlock:
    """ Class for construction of pulse sequences.

    PulseBlock is essentially a container which has several "shelves" (channels),
    and each pulse is represented by a "box" (Pulse object) sitting on the shelf.
    Each "box" must have a name tag: "channel name - start time - duration".
    PulseBlock makes no additional assumptions about the contents of the boxes.

    Since the "boxes" do not necessarily cover the entire duration, there are
    some gaps. To specify what is happening during the gaps, one uses DfltPulse
    objects - "default pulses" (a single DfltPulse per channel).

    PulseBlock handles everything related to keeping the "boxes" time-ordered
    when new elements are added: it has methods for inserting additional "boxes"
    into arbitrary (empty) places on the "shelf" and for merging several smaller
    PulseBlocks into a large one.


    --------------- Structure ---------------

    The main attribute of PulseBlock object is p_dict - the pulse dictionary.
    This is where the entire pulse sequence is stored. In the dictionary:
        Key - the channel name;
        Value - time-ordered list of Pulse objects for this channel.

    After any operation, time axis origin is shifted for the entire PulseBlock
    such that the beginning of earliest Pulse is set to 0.

    PulseBlock assumes that each Pulse object has the following attributes:
        ch - (str) channel name;
        t0 - (numeric) pulse start time;
        dur - (numeric) duration of the pulse,

    dflt_dict attribute contains the default pulse objects:
        Key - (str) channel name
        Value - DfltPulse object

    In addition, PulseBlock has the following attributes:
        name (str) - name of the sequence
        dur (numeric) - total duration of the sequence
                        (t0+dur of the latest Pulse object)
    """

    def __init__(self, p_obj_list=None, dflt_dict=None, name=''):
        """ Construct new PulseBlock.

        Each argument is optional. One can pass non-default values to fill-in
        some of the attributes during construction, but any pulses can be added
        into any location later. Name can also be changed later.

        :param p_obj_list: (opt) list of Pulse objects.
            This argument is used to insert some pulses immediately at instantiation.
            Example:
                p_obj_list = [
                    pulse.PTrue(ch='ch1', t0=0, dur=1e-6),
                    pulse.PSin(ch='ch2', t0=1e-6, dur=1e-6, amp=1e-3, freq=2.5e9, ph=0)
                ]

        :param dflt_dict: (opt) dictionary of default-pulse values.
            Keys - channel names, values - DfltPulse objects
            Can be filled-in at any point later - optional at instantiation.
            Example:
                dflt_dict = {
                    'aom': pulse.DFalse()
                    'analog_out': pulse.DConst(val=0.0)
                }

        :param name: (opt, str) pulse object name
        """

        self.name = name
        self.dur = 0
        self.p_dict = dict()
        self.dflt_dict = dict()

        if dflt_dict is not None:
            self.dflt_dict = copy.deepcopy(dflt_dict)

        if p_obj_list is None:
            p_obj_list = list()

        # Iterate through all given pulses and _insert them into the block
        # (_insert should be used - it does not reset edges)
        for p_obj in p_obj_list:
            p_obj = copy.deepcopy(p_obj)
            self._insert(p_obj=p_obj)

        # Reset edges: set the left-most edge to zero
        # and set self.dur to the right-most edge
        self.reset_edges()

    def _insert(self, p_obj, cflct_er=True):
        """ Technical method for inserting a new Pulse object into PulseBlock
        Here start and stop edges of PulseBlock are not adjusted.

        Insertion location is specified by Pulse object p_obj attributes:
            ch - which channel to insert into. If the specified channel is not
                 yet present in the PulseBlock, the new channel is registered.

            t0 - time to place the beginning of the p_obj with respect to the
                 beginning of PulseBlock. If t0 is negative, p_obj is inserted
                 before the earliest pulse in PulseBlock. Time origin is NOT
                 adjusted - p_obj will have negative t0.

        :param p_obj: the Pulse object to be inserted

        :param cflct_er: (bool) 'conflict-error' check.
                         If True, before actually inserting p_obj, a check is
                         performed to ensure that p_obj does not overlap with
                         existing pulses on the channel. In the case of overlap,
                         PulseBlock is not altered and ValueError is produced.
        :return: None
        """

        p_obj = copy.deepcopy(p_obj)
        ch = p_obj.ch

        # Sanity check:
        #   new pulse does not conflict with existing pulses
        if cflct_er and ch in self.p_dict.keys():

            p_list = self.p_dict[ch]

            # Find the position, into which
            # the new pulse should be inserted
            t0_list = np.array(
                [p_item.t0 for p_item in p_list]
            )
            idx = np.searchsorted(t0_list, p_obj.t0)

            # If the new pulse will not be the left-most [idx = 0],
            # check for overlap with existing pulse to the left
            if idx > 0:
                if not (p_list[idx - 1].t0 + p_list[idx - 1].dur) <= p_obj.t0:
                    cflct_item = p_list[idx - 1]

                    raise ValueError(
                        'insert(): conflict on ch="{}":  given pulse \n'
                        '   {}, t0={:.2e}, dur={:.2e} \n'
                        'overlaps with existing pulse to the left \n'
                        '   {}, t0={:.2e}, dur={:.2e}'
                        ''.format(
                            ch,
                            str(p_obj),
                            p_obj.t0,
                            p_obj.dur,
                            str(cflct_item),
                            cflct_item.t0,
                            cflct_item.dur
                        )
                    )

            # If the new pulse will not be the right-most [idx = len-1],
            # check for overlap with existing pulse to the right
            if idx < len(p_list):
                if not (p_obj.t0 + p_obj.dur) <= p_list[idx].t0:
                    cflct_item = p_list[idx]

                    raise ValueError(
                        'insert(): conflict on ch="{}": given pulse \n'
                        '   {} t0={:.2e}, dur={:.2e} \n'
                        'overlaps with existing pulse to the right \n'
                        '   {} t0={:.2e}, dur={:.2e}'
                        ''.format(
                            ch,
                            str(p_obj),
                            p_obj.t0,
                            p_obj.dur,
                            str(cflct_item),
                            cflct_item.t0,
                            cflct_item.dur
                        )
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

    def insert(self, p_obj, cflct_er=True):
        """ Insert a new Pulse object into PulseBlock

        Insertion location is specified by Pulse object p_obj attributes:
            ch - which channel to insert into. If the specified channel is not
                 yet present in the PulseBlock, the new channel is registered.

            t0 - time to place the beginning of the p_obj with respect to the
                 beginning of PulseBlock. If t0 is negative, p_obj is inserted
                 before the earliest pulse in PulseBlock and time origin is
                 shifted into the beginning of p_obj.

        :param p_obj: the Pulse object to be inserted

        :param cflct_er: (bool) 'conflict-error' check.
                         If True, before actually inserting p_obj, a check is
                         performed to ensure that p_obj does not overlap with
                         existing pulses on the channel. In the case of overlap,
                         PulseBlock is not altered and ValueError is produced.
        :return: None
        """

        self._insert(p_obj=p_obj, cflct_er=cflct_er)
        self.reset_edges()

    def join(self, p_obj, name='', cflct_er=True):
        """ Same as insert(), but instead of changing the existing PulseBlock,
        a new one is created and the original PulseBlock is not altered.

        :param name: name of the new PulseBlock object
        :return: (PulseBlock) the new PulseBlock - self with p_obj inserted.
        """

        new_pb = copy.deepcopy(self)
        new_pb.name = name
        new_pb.insert(
            p_obj=p_obj,
            cflct_er=cflct_er
        )

        return new_pb

    def append(self, p_obj, join=False, name=None, cflct_er=True):
        """ Same as insert()/join(), but t0 of p_obj now refers to the position
        with respect to the end of PulseBlock.

        :param join: (bool) - if False, the existing PulseBlock is modified
                              [insert() method is called, name param is not used]
                              if True, new PulseBlock with name 'name'
                              is created [join() method is called]
        """

        p_obj = copy.deepcopy(p_obj)
        p_obj.t0 += self.dur

        if join:

            if name is None:
                name = self.name

            return self.join(
                p_obj=p_obj,
                name=name,
                cflct_er=cflct_er
            )

        else:
            self.insert(
                p_obj=p_obj,
                cflct_er=cflct_er
            )

    def insert_pb(self, pb_obj, t0=0, cflct_er=True):
        """ Insert PulseBlock pb_obj into self.

        :param pb_obj: the PulseBlock object to be inserted

        :param t0: position where the beginning of pb_obj should be placed with
                   respect to the beginning of self.
                   If t0 is negative, pb_obj is inserted before the beginning of
                   self and time origin is shifted into the beginning of pb_obj.

        :param cflct_er: (bool) If True, conflict check is performed across all
                         channels (for both Pulse and DfltPulse values).

        :return: None
        """

        # TODO: re-implement using reset_edges()

        pb_obj = copy.deepcopy(pb_obj)

        #
        # Sanity checks
        #

        # No overlap between blocks
        if cflct_er and (set(self.p_dict.keys()) & set(pb_obj.p_dict.keys())):
            if t0 >= 0:
                if not self.dur <= t0:
                    raise ValueError(
                        'insert_pb(): blocks overlap and cannot be merged: \n'
                        '   t0={:.2e} does not exceed self.dur={:.2e}'
                        ''.format(t0, self.dur)
                    )
            else:
                if not pb_obj.dur <= abs(t0):
                    raise ValueError(
                        'insert_pb(): blocks overlap and cannot be merged: \n'
                        '   offset -t0={:.2e} is smaller than pb_obj.dur={:.2e}'
                        ''.format(-t0, pb_obj.dur)
                    )
        # No conflicts between default pulse objects
        if cflct_er:
            for ch in pb_obj.dflt_dict.keys():
                if ch in self.dflt_dict.keys() and pb_obj.dflt_dict[ch] != self.dflt_dict[ch]:
                    raise ValueError(
                        'insert_pb(): conflict between default pulse objects on channel "{}": \n'
                        '   self.dflt_dict[{}] = {} \n'
                        ' pb_obj.dflt_dict[{}] = {}'
                        ''.format(
                            ch,
                            ch,
                            str(self.dflt_dict[ch]),
                            ch,
                            str(pb_obj.dflt_dict[ch])
                        )
                    )

        #
        # Insert pb
        #

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

    def join_pb(self, pb_obj, t0=0, cflct_er=True, name=''):
        """ Same as insert_pb(), but instead of modifying self,
        a new PulseBlock is created. Self is not altered.

        :return: (PulseBlock) new PulseBlock - self with pb_obj inserted.
        """

        new_pb = copy.deepcopy(self)
        new_pb.name = name
        new_pb.insert_pb(
            pb_obj=pb_obj,
            t0=t0,
            cflct_er=cflct_er
        )
        return new_pb

    def append_pb(self, pb_obj, offset=0, join=False):
        """ Same as insert_pb()/join_pb(), but now the position for the beginning
        of pb_obj to be placed into should be given with respect to the end of self.

        :param offset: the position into which the beginning of pb_obj should be
                       placed with respect to the end of self.

                       NOTE: only NON-negative offset is allowed.
                       To achieve negative offset, use insert_pb()/join_pb()
        """

        if offset < 0:
            raise ValueError(
                'append_pb(): only non-negative offset is allowed. \n'
                'Use insert_pb() or join_pb() for arbitrary t0'
            )

        if join:
            return self.join_pb(
                pb_obj=pb_obj,
                t0=self.dur + offset,
                name=self.name
            )
        else:
            self.insert_pb(
                pb_obj=pb_obj,
                t0=self.dur + offset
            )

    def reset_edges(self):

        p_ch_list = list(self.p_dict.keys())
        if len(p_ch_list) == 0:
            self.dur = 0
            return

        # Left edge ==============

        # Find the left-most edge - it will be set to origin
        left_edge_list = [
            self.p_dict[ch][0].t0 for ch in p_ch_list
        ]
        left_edge = min(left_edge_list)

        # Shift all pulses such that the left-most edge
        # coincides with zero
        for ch in p_ch_list:
            for p_item in self.p_dict[ch]:
                p_item.t0 -= left_edge

        # Right edge ==============

        # Find the right-most edge - the duration of the block
        right_edge_list = [
            self.p_dict[ch][-1].t0 + self.p_dict[ch][-1].dur for ch in p_ch_list
        ]
        self.dur = max(right_edge_list)

    def __str__(self):
        """ Print PulseBlock

        :return: (str) formatted printout of PulseBlock
        """

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

    # Experiment-oriented convenience utils

    def ch_map(self, map_dict):
        """ Rename channels.

        This method is supposed to be used when high-level, human-readable
        channel names need to be mapped onto hardware-specific channel name
        strings.
        For example: 'mw_drive' -> 'AO1', 'AOM_gate' -> 'DO1'

        :param map_dict: (dict) Name mapping dictionary:
                         Key - current name of the channel in PulseObject;
                         Value - the new name.

                         For example:
                            map_dict = {'mw_drive': 'AO1', 'AOM_gate': 'DO1'}
        :return: None.
        """

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

        # Empty p_dict and dflt_dict
        self.p_dict = dict()
        self.dflt_dict = dict()

        # Fill-in new p_dict with original Pulse lists
        for ch in tmp_p_dict.keys():
            self.p_dict[map_dict[ch]] = tmp_p_dict[ch]

        # Fill-in new dflt_dict with original DfltPulse values
        for ch in tmp_dflt_dict.keys():
            self.dflt_dict[map_dict[ch]] = tmp_dflt_dict[ch]

        # Rename 'ch' attribute in every Pulse object
        for new_ch in self.p_dict.keys():
            for p_item in self.p_dict[new_ch]:
                p_item.ch = new_ch

        del tmp_p_dict, tmp_dflt_dict

    def add_offset(self, offset_dict):
        """ Time-offset several channel.

        This method is supposed to be used to offset all pulses on a given
        channel/channels with respect to the rest of PulseBlock.

        This is normally used when one needs to compensate for the physical delay
        between channels.

        :param offset_dict: (dict) offset dictionary:
                            Key - channel name
                            Value - offset (both positive and negative
                            values are acceptable)
        :return: None.
        """

        # Sanity check: all given channels are present in p_dict

        if not set(offset_dict.keys()) <= set(self.p_dict.keys()):
            raise ValueError(
                'offset dictionary contains unknown channels: \n'
                'offset_dict.keys() = {} \n'
                'self.p_dict.keys() = {}'
                ''.format(
                    sorted(offset_dict.keys()),
                    sorted(self.p_dict.keys())
                )
            )

        for ch in offset_dict.keys():
            offset = offset_dict[ch]

            for p_item in self.p_dict[ch]:
                p_item.t0 += offset

        self.reset_edges()
