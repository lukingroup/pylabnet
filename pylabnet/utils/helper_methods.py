import unicodedata
import os
import time
import re
import sys
import ctypes
import numpy as np
from pylabnet.core.generic_server import GenericServer


def str_to_float(in_val):
    """Convert human-readable exponential form to float.

    :param in_val: (str) input string of the following formats:

            'float_number' --> float_number

            'float_number + white_space + exp_prefix + unit_string'
                                 --> float_number * 10**exp_value

        Supported exp prefixes: ['T', 'G', 'M', 'k', '', 'm', 'u', 'n', 'p']

        Warning: format 'just exp_prefix without unit_string' is not
        supported: if only one symbol is given after 'float_number',
        it will be interpreted as unit and exponent will be set to 10**0.

        Examples: '1.2 us'   --> 1.2e-6
                  '-4.5 mV'  --> -4.5e-3
                  '10.1 GHz' --> 1.01e10
                  '1.56 s'   --> 1.56
                  '1.56 m'   --> 1.56 [interpreted as 1.56 meters, not as 1.56e-3]

    :return: (float) extracted value without unit
    """

    if isinstance(in_val, (float, int)):
        return in_val

    # Split string into mantissa and exp_prefix + unit
    item_list = in_val.split()

    # Extract mantissa exp_prefix if included
    mantissa = float(item_list[0])
    # Extract exp_prefix (a single letter) if included
    try:
        exp_prefix_unit = item_list[1]

        if len(exp_prefix_unit) > 1:
            exp_prefix = item_list[1][0]
        else:
            exp_prefix = ''

    except IndexError:
        exp_prefix = ''

    # Convert exp_prefix into exp_value
    if exp_prefix == 'T':
        exp_value = 12
    elif exp_prefix == 'G':
        exp_value = 9
    elif exp_prefix == 'M':
        exp_value = 6
    elif exp_prefix == 'k':
        exp_value = 3
    elif exp_prefix == '':
        exp_value = 0
    elif exp_prefix == 'm':
        exp_value = -3
    elif exp_prefix == 'u':
        exp_value = -6
    elif exp_prefix == 'n':
        exp_value = -9
    elif exp_prefix == 'p':
        exp_value = -12
    else:
        # The case of multi-letter unit without prefix: '1.5 Hz'
        # the first letter 'H' is not an exp prefix
        exp_value = 0

    return mantissa * (10 ** exp_value)


def pwr_to_float(in_val):

    # FIXME: implement

    # if isinstance(in_val, float):
    #     return in_val
    # #
    # # Determine whether the power is given in Volts or dBm
    # #
    # # Split string into mantissa and exp_prefix + unit
    # item_list = in_val.split()
    #
    # # Extract exp_prefix (a single letter) if included
    # try:
    #     exp_prefix_unit = item_list[1]
    #
    #     if len(exp_prefix_unit) > 1:
    #         exp_prefix = item_list[1][0]
    #     else:
    #         exp_prefix = ''
    # except IndexError:
    #     exp_prefix = ''

    return str_to_float(in_val=in_val)


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.

    From Django 2.2
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower()).strip()
    return re.sub(r'[-\s]+', '-', value)


def get_dated_subdirectory_filepath(directory, filename):
    '''Creates directory structure folder_path/YEAR/MONTH/DAY/filename

    :folder_path: Upper level directory
    :filename: Name of file. Will be slugified.

    Return:
    :filepath: Path to file in newly created structure.
    '''

    # Create subdirectory structure: YEAR/MONTH/DAY
    dated_path = os.path.join(directory, time.strftime('%Y'), time.strftime('%m'), time.strftime('%d'))

    # create folders if they don't exists yet
    os.makedirs(dated_path, exist_ok=True)

    # Define full file path
    filepath = os.path.join(dated_path, f'{slugify(filename)}.log')

    return filepath


def dict_to_str(dic, separate='\n'):
    """ Converts a dictionary to a nicely formatted string

    :param dic: (dict) to convert
    :param separate: (str) string to use to separate dictionary elements
    :return: (str) of dictionary content
    """

    dict_str = ''
    for key, value in dic.items():
        dict_str += '{}: {}{}'.format(key, value, separate)

    return dict_str.rstrip()


def remove_spaces(st):
    """ Removes spaces from a string

    :param st: (str) input string with spaces
    :return: (str) string without any spaces
    """

    return st.replace(' ', '')


def parse_args():
    """ Parses command line arguments into dictionary format, assuming keywords of the form --kw for each argument"""

    arg_index = 1
    arg_dict = {}
    while arg_index < len(sys.argv) - 1:
        arg_dict[sys.argv[arg_index][2:]] = sys.argv[arg_index + 1]
        arg_index += 2

    return arg_dict

def unpack_launcher(**kwargs):
    """ Unpacks the launcher kwargs for easy use in launcher method definition within script modules.
    Copy paste the following implementation at the top of script.launch() method:

    logger, logport, clients, guis, params = unpack_launcher(**kwargs)

    :param kwargs: (dict) contains all keyword arguments required for launching a script from launcher module
        e.g.: dict(logger=log, clients=[client1, client2], guis=[gui_client1, gui_client2]),
                   logport=1234, params=experimental_parameters_container)
        Note that experimental parameters should go in "params" and can be customized to contain all other
        script specific stuff

    :return: (tuple) logger, logport, clients, guis, params
    """

    logger = kwargs['logger']
    clients = kwargs['clients']
    guis = kwargs['guis']
    logport = kwargs['logport']
    params = kwargs['params']

    return (logger, logport, clients, guis, params)

def show_console():
    """ Shows the active console.

    Useful for processes where console is typically hidden but user input is suddenly required
    """

    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 9)

def hide_console():
    """ Hides the active console.

    Useful for processes where console is not needed (isntead, there is a GUI to use)
    """

    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)

def create_server(service, logger=None, host='localhost'):
    """ Attempts to create a server with randomly chosen port numbers

    :param service: service from which to launch a server
    :param logger: instance of LogClient for logging
    :param host: (optinal) IP address of host

    :return: (tuple) instance of server created, port number (int) created on
    """

    timeout = 0
    while timeout < 1000:
        try:
            port = np.random.randint(1, 9999)
            server = GenericServer(
                host='localhost',
                port=port,
                service=service
            )
            timeout = 9999
        except ConnectionRefusedError:
            msg_str = f'Failed to create update server with port {port}'
            if logger is None:
                print(msg_str)
            else:
                logger.warn(f'Failed to create update server with port {port}')
            timeout += 1
    return server, port
