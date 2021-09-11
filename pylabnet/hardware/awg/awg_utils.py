"""Useful generic util functions for controlling the DIO breakout / AWG"""
from pylabnet.utils.helper_methods import load_config


def convert_awg_pin_to_dio_board(awgPinNumber, configFN="awg_dio_pin_mapping"):
    """Computes the corresponding board and channel number on the DIO breakout for the
        corresponding input awgPinNumber given the mapping specificed in the configuration
        file provided.
    """
    #First load the mapping config file
    config = load_config(configFN)
    #Get base pin index for board 0,1 and 2,3
    baseB01 = config["B01_base"]
    baseB23 = config["B23_base"]

    currBase = 0
    board = 0

    #Now checking to see which board corresponds with our AWG pin index
    if awgPinNumber >= baseB01 and awgPinNumber < baseB01 + 8:
        #Corresponds with boards 0, 1
        board = 0
        currBase = baseB01
    elif awgPinNumber >= baseB23 and awgPinNumber < baseB23 + 8:
        #Corresponds with boards 2, 3
        board = 2
        currBase = baseB23
    else:
        #Means pin number is not covered by range of those currently connected to the dio
        raise Exception("Invalid pin number")

    #Finally figure out the channel number within the pair of boards
    channel = awgPinNumber - currBase
    if (channel >= 4):
        #If we are beyond channel 4, we are actually on the 2nd board in the pair so update accordingly
        channel = channel - 4
        board = board + 1

    return board, channel


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
