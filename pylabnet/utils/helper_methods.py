import unicodedata
import os
import time
import json
import re
import sys
import ctypes
import copy
import numpy as np
import subprocess
from datetime import date, datetime
from pylabnet.network.core.generic_server import GenericServer
import pyqtgraph as pg
import pyqtgraph.exporters


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


def get_dated_subdirectory_filepath(directory, filename=None):
    '''Creates directory structure folder_path/YEAR/MONTH/DAY/filename

    :folder_path: Upper level directory
    :filename: Name of file. Will be slugified. If None just returns directory

    Return:
    :filepath: Path to file in newly created structure.
    '''

    # Create subdirectory structure: YEAR/MONTH/DAY
    dated_path = os.path.join(directory, time.strftime('%Y'), time.strftime('%m'), time.strftime('%d'))

    # create folders if they don't exists yet
    os.makedirs(dated_path, exist_ok=True)

    # Define full file path
    if filename is None:
        filepath = dated_path
    else:
        filepath = os.path.join(dated_path, f'{slugify(filename)}')

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

    logger, loghost logport, clients, guis, params = unpack_launcher(**kwargs)

    :param kwargs: (dict) contains all keyword arguments required for launching a script from launcher module
        e.g.: dict(logger=log, loghost='localhost', clients=[client1, client2], guis=[gui_client1, gui_client2]),
                   logport=1234, params=experimental_parameters_container)
        Note that experimental parameters should go in "params" and can be customized to contain all other
        script specific stuff

    :return: (tuple) logger, logport, clients, guis, params
    """

    logger = kwargs['logger']
    loghost = kwargs['loghost']
    clients = kwargs['clients']
    guis = kwargs['guis']
    logport = kwargs['logport']
    params = kwargs['params']


    return logger, loghost, logport, clients, guis, params


def show_console():
    """ Shows the active console.

    Useful for processes where console is typically hidden but user input is suddenly required
    """

    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 9)

def hide_console():
    """ Hides the active console.

    Useful for processes where console is not needed (isntead, there is a GUI to use)
    """

    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

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
            port = np.random.randint(1024, 49151)
            server = GenericServer(
                host=host,
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

def setup_full_service(service_class, module, logger=None, host='localhost'):
    """ Creates a Service and a server, adds info to logger and starts server

    :param service_class: Service class to instantiate (not the instance itself)
    :param module: module to assign to service
    :param logger: instance of LogClient
    :param host: (str) hostname
    """

    service = service_class()
    service.assign_module(module)
    server, port = create_server(service, logger=logger, host=host)
    logger.update_data(data=dict(port=port))
    server.start()

def value_to_bitval(value, bits=8, min=0, max=1):
    """ Converts a value to a bits-bit number for range min to max

    :param value: (float) value to convert
    :param bits: (int) number of bits of resolution
    :param min: (float) minimum of range
    :param max: (float) maximum of range

    :return: (int) value in bits-bit (e.g. 8-bit from 0 to 2^8-1)
    """

    # Convert value to scale of 0 to 1
    scaled_value = (value-min)/(max-min)

    return int(scaled_value * (2**bits - 1))

def bitval_to_value(bitval, bits=8, min=0, max=1):
    """ Converts a bits-bit number into its physical value for range from min to max

    :param bitval: (int)  value in bits-bit (e.g. 8-bit from 0 to 2^8-1)
    :param bits: (int) number of bits of resolution
    :param min: (float) minimum of range
    :param max: (float) maximum of range

    :return: (float) physical value
    """

    # Convert value to scale of 0 to 1
    scaled_value = bitval/(2**bits - 1)

    return scaled_value*(max-min) + min

def generate_widgets(widget_dict):
    """ Generates a list of widget names based on a supplied dictionary

    Assumes widgets follow a naming convention of "widget_base_name_i" where i is the index
    (this function is helpful when one has many widgets with the same base_name)
    :param widget_dict: (dict) containing widget base names as keys, and number of instances as
        values
    """

    widgets = ()
    for widget_name, instances in widget_dict.items():
        widgets = widgets + ([f'{widget_name}_{instance+1}' for instance in range(instances)],)
    return widgets


def generate_filepath(filename=None, directory=None, date_dir=False):
    """ Generates filepath for saving.

    :param dir: (str) directory to save to
    :param filename: (str) name of file to save
    :param date_dir: (bool) whether or not to use date sub-directory
    """

    if directory is None:
        directory = os.getcwd()
    if filename is None:
        filename = str(datetime.now().strftime('%H_%M_%S'))
    else:
        filename += str(datetime.now().strftime('_%H_%M_%S'))
    if date_dir:
        filepath = get_dated_subdirectory_filepath(directory, filename)
    else:
        filepath = os.path.join(directory, filename)

    return filepath

def generic_save(data, filename=None, directory=None, date_dir=False):
    """ Saves data as txt file

    :param dir: (str) directory to save to
    :param filename: (str) name of file to save
    :param date_dir: (bool) whether or not to use date sub-directory
    """

    filepath = generate_filepath(filename, directory, date_dir)
    if not filepath.endswith('.txt'):
        filepath += '.txt'

    try:
        np.savetxt(filepath, data)
    except OSError:
        os.mkdir(directory)
        np.savetxt(filepath, data)
    except ValueError:
        # TODO: Potentially incorporate with logger and except hook
        pass


def save_metadata(log, filename=None, directory=None, date_dir=False):
    """ Saves metadata stored in the logger

    :param log: (LogClient)
    :param dir: (str) directory to save to
    :param filename: (str) name of file to save
    :param date_dir: (bool) whether or not to use date sub-directory
    """

    filepath = generate_filepath(f'{filename}_metadata', directory, date_dir)
    if not filepath.endswith('.json'):
        filepath += '.json'

    try:
        with open(filepath, 'w') as outfile:            
            json.dump(log.get_metadata(), outfile, indent=4)
    except TypeError:
        log.warn('Did not save metadata')
    except OSError:
        log.warn('Did not save metadata')


def plotly_figure_save(plotly_figure, filename=None, directory=None, date_dir=False):
    """ Saves plotly_figure as png

    :param dir: (str) directory to save to
    :param filename: (str) name of file to save
    :param date_dir: (bool) whether or not to use date sub-directory
    """

    filepath = generate_filepath(filename, directory, date_dir)
    plotly_figure.write_image(f'{filepath}.png')

def pyqtgraph_save(widget, filename=None, directory=None, date_dir=False):
    """ Saves pyqtgraph figure to png

    :param dir: (str) directory to save to
    :param filename: (str) name of file to save
    :param date_dir: (bool) whether or not to use date sub-directory
    """

    filepath = generate_filepath(filename, directory, date_dir)+'.png'
    exporter = pg.exporters.ImageExporter(widget)
    exporter.export(filepath)

def load_config(config_filename, folder_root=None, logger=None):
    """ Load configuration data stored in JSON format

    :config_filename: (str) Name of config. file, wihtout the .json ending
    :folder_root: (str) Name of folder where the config files are stored. If None,
       use pylabnet/config
    :logger: (object) Instance of logger.

    Returns data as python dictionary, or None if
    """

    filepath = get_config_filepath(config_filename, folder_root)

    try:
        # Opening JSON file
        f = open(filepath)

        # returns JSON object as
        # a dictionary
        data = json.load(f)
        try:
            logger.info(f'Successfully loaded settings from {config_filename}.json.')
        # Dont raise error if logger doesn't exist
        except AttributeError:
            pass
    except FileNotFoundError:
        data = None
        try:
            logger.error(f'Settings file {filepath} not found.')
        except AttributeError:
            raise

    return data

def get_config_directory():
    """ Returns the config directory """

    return os.path.abspath(os.path.join(
        os.path.dirname( __file__ ),
        '..',
        'configs'
    ))

def load_device_config(device, config, logger=None):
    """ Returns the device config directory 
    
    :param device: (str) name of the device folder
    :param config: (str) name of the specific device config file
    :param logger: instance of LogHandler
    """

    filepath = os.path.join(get_config_directory(), 'devices', device, f'{config}.json')
    try:
        f = open(filepath)
        # returns JSON object as
        # a dictionary
        data = json.load(f)
        try:
            logger.info(f'Successfully loaded settings from {config}.json.')
        # Dont raise error if logger doesn't exist
        except AttributeError:
            pass

    except FileNotFoundError:
        data = None
        try:
            logger.error(f'Settings file {filepath} not found.')
        except AttributeError:
            raise
    return data

def load_script_config(script, config, logger=None):
    """ Returns the script config directory 
    
    :param script: (str) name of the script folder
    :param config: (str) name of the specific script config file
    :param logger: instance of LogHandler
    """

    filepath = os.path.join(get_config_directory(), 'scripts', script, f'{config}.json')
    try:
        f = open(filepath)
        # returns JSON object as
        # a dictionary
        data = json.load(f)
        try:
            logger.info(f'Successfully loaded settings from {config}.json.')
        # Dont raise error if logger doesn't exist
        except AttributeError:
            pass

    except FileNotFoundError:
        data = None
        try:
            logger.error(f'Settings file {filepath} not found.')
        except AttributeError:
            raise
    return data

def get_config_filepath(config_filename, folder_root=None):
    """ Gets the config filepath

    :param config_filename: (str) name of configuration file to save.
        Can be an existing config file with other configuration parameters
    :folder_root: (str) Name of folder where the config files are stored. If None,
       use pylabnet/config
    """

    if folder_root is None:
        filepath = os.path.abspath(
            os.path.join(
                os.path.dirname( __file__ ),
                '..',
                'configs',
                f'{config_filename}.json'
            )
        )
    else:
        filepath = os.path.join(folder_root, f'{config_filename}.json')

    return filepath

def get_gui_widgets(gui, **kwargs):
    """ Returns the GUI widget objects specified in kwargs

    :param gui: (Window) main window gui object containing other widgets
    :param kwargs: keyword arguments with argument name being the name
        of the widget (str, widget_name) and argument value an integer specifying the
        number of copies of that widget

        For more than 1 widget copy, assumes the name is assigned as
        widget_name_1, widget_name_2, etc.

    :return: (dict) dictionary with keywords as widget name and values
        as either individual widgets or list of widgets in case of multiple
        similarly named widgets
    """

    widgets = dict()
    for widget_name, widget_number in kwargs.items():

        # Check if it is multiple named widgets
        if widget_number > 1:
            widget_list = []
            for widget_index in range(widget_number):
                widget_list.append(getattr(
                    gui,
                    f'{widget_name}_{widget_index+1}'
                ))
            widgets[widget_name] = widget_list
        else:
            widgets[widget_name] = getattr(gui, widget_name)

    return widgets

def get_legend_from_graphics_view(legend_widget: pg.GraphicsView):
    """ Configures and returns a legend widget given a GraphicsView

    :param legend_widget: instance of GraphicsView object
    :return: pg.LegendItem
    """

    legend = pg.LegendItem()
    view_box = pg.ViewBox()
    legend_widget.setCentralWidget(view_box)
    legend.setParentItem(view_box)
    legend.anchor((0, 0), (0, 0))

    return legend

def add_to_legend(legend: pg.LegendItem, curve: pg.PlotItem, curve_name):
    """ Adds a curve to a legend

    :param legend: pg.LegendItem to add to
    :param curve: pg.PlotItem containing the relevant curve
    :param curve_name: (str) name of curve
    """

    legend.addItem(
        curve,
        ' - '+curve_name
    )

def fill_2dlist(list_in):
    """ Turns a 2D list of irregular dimensions into a 2D numpy array

    Assuming only last dimension of list is incomplete
    :param list_in: input list
    :return: (numpy.ndarray) 2D array with missing elements padded as zeros
    """

    list_manipulate = copy.deepcopy(list_in)
    if len(list_in) > 1:
        list_manipulate[-1] += [list_manipulate[-1][0]]*(len(list_manipulate[0])-len(list_manipulate[-1]))

    return np.array(list_manipulate)

def find_keys(input_dict, key_name):
    """Returns value of dictionary if key_name is either the key of the dict (normal dictionary lookup),
    or an element of a key that is a tuple or list.

    :input_dict: Dictionary to search.
    :key_name: Key to lookup.
    """

    found = [ ]
    for k, v in input_dict.items():
        if type(k) in [list, tuple, dict] and key_name in k:
            found.append(v)
        elif key_name == k:
           found.append(v)

    return found

def find_client(logger, client_dict, client_name):
    """Finds client from unpacked launcher client dictionary."""
    found_clients = find_keys(client_dict, client_name)

    num_clients = len(found_clients)

    if num_clients == 0:
        logger.error(f'Client {client_name} could not be found.')
    elif num_clients > 1:
        logger.error(f"Multiple ({num_clients}) with name {client_name} found.")
    else:
        return found_clients[0]

def launch_device_server(server, config, log_ip, log_port, server_port, debug=False):
    """ Launches a new device server """

    config_dict = load_device_config(server, config)
    launch_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        'launchers',
        'pylabnet_server.py'
    )

    if server_port is None:
        server_port = np.random.randint(1024, 49151)

    # Build command
    cmd = f'start "{server}_server, '
    cmd += time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
    cmd += f'" "{sys.executable}" "{launch_path}" '
    cmd += f'--logip {log_ip} --logport {log_port} '
    cmd += f'--serverport {server_port} --server {server} '
    cmd += f'--device_id "{config_dict["device_id"]}" '
    cmd += f'--config {config} --debug {debug}'

    if 'ssh_config' in config_dict:
        # TODO: perform SSH
        pass

    subprocess.Popen(cmd, shell=True)

def launch_script(script, config, log_ip, log_port, debug_flag, server_debug_flag, num_clients, client_cmd):
    """ Launches a script """

    launch_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        'launchers',
        'launcher.py'
    )

    # Build command
    cmd = f'start "{script}_server, '
    cmd += time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
    cmd += f'" "{sys.executable}" "{launch_path}" '
    cmd += f'--logip {log_ip} --logport {log_port} '
    cmd += f'--script {script} --num_clients {num_clients} '
    cmd += f'--config {config} --debug {debug_flag} '
    cmd += f'--server_debug {server_debug_flag}'
    cmd += client_cmd

    subprocess.Popen(cmd, shell=True)
