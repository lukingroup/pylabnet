"""Useful generic util functions for controlling the DIO breakout / AWG"""
from pylabnet.utils.helper_methods import load_config


def convert_awg_pin_to_dio_board(awgPinNumber, breakout_dio_pin_mapping):
    """Computes the corresponding board and channel number on the DIO breakout for the
        corresponding input awgPinNumber given the mapping specificed in the configuration
        file provided.
    """

    # Check that no channels are duplicated
    allocated_chs = []
    for board in breakout_dio_pin_mapping:
        allocated_chs.extend(list(range(board["ch_start"], board["ch_end"] + 1)))

    # If there are duplicates, reject the mapping
    if len(allocated_chs) != len(set(allocated_chs)):
        raise ValueError("Invalid pin mapping, duplicated channels. ")

    # Get the board that the desired pin lies on
    for board in breakout_dio_pin_mapping:
        if board["ch_start"] <= awgPinNumber <= board["ch_end"]:
            board_num = board["board_num"]
            channel = awgPinNumber - board["ch_start"] # channel number on that board
            return board_num, channel

    # If we reach here, it means we failed to find a channel
    raise ValueError("Invalid pin number")


def main():
    board, channel = (convert_awg_pin_to_dio_board(24))
    print(board, channel)

    board, channel = (convert_awg_pin_to_dio_board(27))
    print(board, channel)

    board, channel = (convert_awg_pin_to_dio_board(26))
    print(board, channel)

    board, channel = (convert_awg_pin_to_dio_board(28))
    print(board, channel)

    board, channel = (convert_awg_pin_to_dio_board(31))
    print(board, channel)


if __name__ == "__main__":
    main()
