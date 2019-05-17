import logic.pulsed.pulse_func as pf
from utils.helper_methods import str_to_float
import numpy as np
import copy


class PulseBlock:

    def __init__(self, *init_list):

        # init_list = [
        #     PulseParam('chnl', position, [duration], [p_func]),
        #     PulseParam('chnl', position, [duration], [p_func]),
        #     ...,
        #     PulseParam('chnl', position, [duration], [p_func])
        # ]

        # Pulse table of this pulse block:
        # {
        #   'chnl_name_1': [p_func_bin_1, ... , p_func_bin_N],
        #   'chnl_name_2': [p_func_bin_1, ... , p_func_bin_N],
        #   ...
        #   'chnl_name_n': [p_func_bin_1, ... , p_func_bin_N]
        # }
        self.pulse_dict = dict()

        self.chnl_set = set()

        self.bin_edge_list = np.array([], dtype=np.float)
        self.bin_len_list = np.array([], dtype=np.float)
        self.bin_mid_list = np.array([], dtype=np.float)
        self.bin_number = 0

        self.duration = 0

        # Build chnl_set
        # [set() is an unordered collections of unique elements]
        for pulse in init_list:
            self.chnl_set.add(pulse.chnl)

        # Build bin_edge_list
        bin_edge_set = set()
        for pulse in init_list:
            bin_edge_set.add(pulse.position)
            bin_edge_set.add(pulse.position + pulse.duration)
        # convert to numpy.array and sort
        self.bin_edge_list = np.array(list(bin_edge_set), dtype=np.float)
        self.bin_edge_list.sort()

        # Calculate bin_len_list
        self.bin_len_list = np.diff(self.bin_edge_list)

        # Calculate bin_mid_list
        self.bin_mid_list = self.bin_edge_list[:-1] + 0.5*self.bin_len_list

        # Calculate bin_number and total duration
        self.bin_number = len(self.bin_len_list)
        self.duration = np.sum(self.bin_len_list)

        # Iterate though chnl_set and for each channel
        # fill-in bin array with corresponding p_func
        for chnl in self.chnl_set:

            # Init bin array for this channel
            self.pulse_dict[chnl] = []

            # collect all requested pulses on this channel
            chnl_pulse_list = []
            for pulse in init_list:
                if pulse.chnl == chnl:
                    chnl_pulse_list.append(
                        dict(
                            start=pulse.position,
                            stop=pulse.position + pulse.duration,
                            p_func=pulse.p_func
                        )
                    )

            # Set default for each bin (will be over-written if pulse was requested)
            self.pulse_dict[chnl] = [pf.Dflt()] * self.bin_number

            # Iterate though every bin and set requested p_func
            for bin_index in range(self.bin_number):

                # check if the bin is covered by one of the pulse requests
                # for this channel and set requested p_func if so
                bin_mid = self.bin_mid_list[bin_index]

                for pulse_req in chnl_pulse_list:
                    if pulse_req['start'] < bin_mid <= pulse_req['stop']:
                        # set requested p_func
                        self.pulse_dict[chnl][bin_index] = pulse_req['p_func']
                        # any bin on a given channel can be covered by only one request
                        # so one can break when first request is fond
                        break

    def iplot(self):
        pass


def pb_merge(*args):

    # Create blank PulseBlock to be returned
    new_pb = PulseBlock()

    #
    # Pre-process all given blocks (and offsets, if specified)
    #
    block_list = []
    for arg_item in args:

        if isinstance(arg_item, PulseBlock):
            # Block given without time offset
            block = copy.deepcopy(arg_item)
            block_list.append(block)

        elif isinstance(arg_item, tuple):
            # A tuple is given: (PulseBlock, time_offset)
            block = copy.deepcopy(arg_item[0])
            t_offset = str_to_float(arg_item[1])

            block.bin_edge_list += t_offset
            block.bin_mid_list += t_offset
            block_list.append(block)

        else:
            raise TypeError(
                'merge(): invalid argument {0}. \n'
                'Argument must be a PulseBlock instance, or a tuple(PulseBlock, offset)'
                ''.format(arg_item)
            )

    #
    # Merge channel sets
    #
    for block in block_list:
        new_pb.chnl_set.add(block.chnl_set)

    #
    # Merge bins
    #

    # Collect all edges in a set
    bin_edge_set = set()
    for block in block_list:
        bin_edge_set.add(block.bin_edge_list)
    # Convert back to numpy array
    bin_edge_list = np.array(bin_edge_set, dtype=np.float)
    bin_edge_list.sort()
    #   shift all edges, if the smallest is negative
    #   [if some blocks were given with negative t_offset]
    if len(bin_edge_list) > 0 > bin_edge_list[0]:
        bin_edge_list -= bin_edge_list[0]

    # Calculate bin_len_list, bin_mid_list, bin_number, and duration
    bin_len_list = np.diff(bin_edge_list)
    bin_mid_list = bin_edge_list[:-1] + 0.5*bin_len_list
    bin_number = len(bin_len_list)
    duration = np.sum(bin_len_list)

    # Set values of new_pb
    new_pb.bin_edge_list = bin_edge_list
    new_pb.bin_len_list = bin_len_list
    new_pb.bin_mid_list = bin_mid_list
    new_pb.bin_number = bin_number
    new_pb.duration = duration

    #
    # Fill-in pulse_dict (the pulse table)
    #

    # Initially fill everything with default p_func
    for chnl in new_pb.chnl_set:
        new_pb.pulse_dict[chnl] = [pf.Dflt()] * new_pb.bin_number

    # Iterate through full bin list
    for bin_index in range(new_pb.bin_number):

        # Iterate through each block and determine
        # whether the bin is covered by the block
        for block in block_list:
            if block.bin_number == 0:
                # empty block
                continue
            bin_mid = new_pb.bin_mid_list[bin_index]
            if not block.bin_edge_list[0] < bin_mid <= block.bin_edge_list[-1]:
                # the bin lies outside of this block
                continue
            else:
                # The block covers this bin
                # Determine index of the block's bin which covers current bin
                # [cover_bin_index]
                for edge_index, edge_val in enumerate(block.bin_edge_list):
                    # Current bin is contained in some of the bins of the block.
                    # Run from left to right and find the first block bin edge,
                    # grater than bin_mid --
                    #                this is the right edge of the covering bin.
                    if bin_mid <= edge_val:
                        cover_bin_index = edge_index - 1
                        break

                # Now the cover_bin_index of the current bin
                # within the block is known

                # Iterate through all channels, mentioned in the block,
                # and set corresponding values to new_pb.pulse_dict
                for chnl in block.chnl_set:
                    new_pb.pulse_dict[chnl][bin_index] = block.pulse_dict[chnl][cover_bin_index]


class PulseParam:

    def __init__(self, chnl, duration, position=None, p_func=None):

        # Set channel name [string]
        self.chnl = chnl

        # Set duration:
        #   handle float [1.2e-9] and string ['1.2 ns']
        if isinstance(duration, (float, int)):
            self.duration = float(duration)
        elif isinstance(duration, str):
            self.duration = str_to_float(duration)
        else:
            raise TypeError(
                'PulseParam(duration={}) invalid argument type. Valid types: float, int, and str'
                ''.format(duration)
            )

        # Set position
        if position is None:
            self.position = 0
        else:
            # handle float [1.2e-9] and string ['1.2 ns']
            if isinstance(position, (float, int)):
                self.position = float(position)
            elif isinstance(position, str):
                self.position = str_to_float(position)
            else:
                raise TypeError(
                    'PulseParam(position={}) invalid argument type. Valid types: float, int, and str'
                    ''.format(position)
                )

        # Set p_func
        if p_func is None:
            self.p_func = pf.Dflt()
        else:
            self.p_func = p_func
