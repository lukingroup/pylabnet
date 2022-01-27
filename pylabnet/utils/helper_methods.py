import unicodedata
import os
import time
import json
import re
import sys
import ctypes
import copy
import numpy as np
import socket
import subprocess
import paramiko
import platform
import decouple
from datetime import datetime
from pylabnet.network.core.generic_server import GenericServer
import pyqtgraph as pg
import pyqtgraph.exporters
#import netifaces as ni


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

    operating_system = get_os()
    if operating_system == 'Windows':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 9)


def hide_console():
    """ Hides the active console.

    Useful for processes where console is not needed (isntead, there is a GUI to use)

    :os: (string) Which operating system is used ('Windows' and 'Linux' supported)
    """

    operating_system = get_os()
    if operating_system == 'Windows':
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
    scaled_value = (value - min) / (max - min)

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
    scaled_value = bitval / (2**bits - 1)

    return scaled_value * (max - min) + min


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

    filepath = generate_filepath(filename, directory, date_dir) + '.png'
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
        os.path.dirname(__file__),
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
                os.path.dirname(__file__),
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
        ' - ' + curve_name
    )


def fill_2dlist(list_in):
    """ Turns a 2D list of irregular dimensions into a 2D numpy array

    Assuming only last dimension of list is incomplete
    :param list_in: input list
    :return: (numpy.ndarray) 2D array with missing elements padded as zeros
    """

    list_manipulate = copy.deepcopy(list_in)
    if len(list_in) > 1:
        list_manipulate[-1] += [list_manipulate[-1][0]] * (len(list_manipulate[0]) - len(list_manipulate[-1]))

    return np.array(list_manipulate)


def find_keys(input_dict, key_name):
    """Returns value of dictionary if key_name is either the key of the dict (normal dictionary lookup),
    or an element of a key that is a tuple or list.

    :input_dict: Dictionary to search.
    :key_name: Key to lookup.
    """

    found = []
    for k, v in input_dict.items():
        if type(k) in [list, tuple, dict] and key_name in k:
            found.append(v)
        elif key_name == k:
            found.append(v)

    return found


def find_client(clients, settings, client_type, client_config=None, logger=None):
    """ Finds a particular client from client dictionary passed from launcher

    :param clients: (dict) client dictionary
    :param settings: (dict) configuration dictionary for script
    :param client_type: (str) type of server (e.g. nidaqmx)
    :param client_config: (str, optional) name of config file for specific device
        only needed if multiple devices of the same type are used in this script
    :param logger: (LogHandler)
    """

    found_clients = find_keys(clients, client_type)
    num_clients = len(found_clients)

    # If no matched clients, log an error
    if num_clients == 0:
        logger.error(f'Client {client_type} could not be found')

    # If > 1 matched clients, try to use the device config file to match
    elif num_clients > 1:
        if client_config is not None:
            device_settings = load_device_config(client_type, client_config, logger)

            # Search through clients using device IDs
            found_clients = find_keys(clients, device_settings['device_id'])

            # If single client, return, otherwise log error
            num_clients = len(found_clients)
            if num_clients == 1:
                return found_clients[0]
            elif num_clients == 0:
                logger.error(f'Client ID {device_settings["device_id"]} not found')
            else:
                logger.error(f'Multiple clients with client ID {device_settings["device_id"]} found')

    # If only 1 matched client, just return
    else:
        return found_clients[0]


def launch_device_server(server, dev_config, log_ip, log_port, server_port, debug=False, logger=None):
    """ Launches a new device server

    :param server: (str) name of the server. Should be the directory in which the
        relevant server config file is located, and should have a corresponding
        launch file server.py in pylabnet.launchers.servers
    :param dev_config: (str) name of the config file for the server, which specifies
        the device_id and also any SSH info
    :param log_ip: (str) logger IP address
    :param log_port: (int) logger port number
    :param server_port: (int) port number of server to use
    :param debug: (bool) whether or not to debug the server launching
    :param logger: (LogHandler)
    """

    # First load device config into dict
    config_dict = load_device_config(server, dev_config)

    if 'disabled' in config_dict and config_dict['disabled'] == 'True':
        msg_str = f'Device {server} launching is disabled'
        if logger is None:
            print(msg_str)
        else:
            logger.error(msg_str)
        return

    # Check if we should SSH in
    if 'ssh_config' in config_dict:
        ssh = True

        # Load SSH parameters
        ssh_params = config_dict['ssh_config']
        hostname = ssh_params['hostname']
        host_ip = ssh_params['ip']

        # SSH in
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        try:
            ssh.connect(host_ip, username=hostname, password=decouple.config('LOCALHOST_PW'))
            msg_str = f'Successfully connected via SSH to {hostname}@{host_ip}'
            if logger is None:
                print(msg_str)
            else:
                logger.info(msg_str)
        except TimeoutError:
            msg_str = f'Failed to setup SSH connection to {hostname}@{host_ip}'
            if logger is None:
                print(msg_str)
            else:
                logger.error(msg_str)

        # Set command arguments
        python_path = ssh_params['python_path']
        launch_path = ssh_params['script_path']
        start = ""

        # Kill processes if required
        if 'kill_all' in ssh_params and ssh_params['kill_all'] == "True":
            msg_str = f'Killing all python processes on {hostname}@{host_ip}'
            if logger is None:
                print(msg_str)
            else:
                logger.warn(msg_str)
            ssh.exec_command('taskkill /F /IM python.exe /T')

    else:
        ssh = False
        start = f'start "{server}_server, '
        start += time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
        start += '" '
        host_ip = get_ip()
        python_path = sys.executable
        launch_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'launchers',
            'pylabnet_server.py'
        )

    if server_port is None:
        server_port = np.random.randint(1024, 49151)

    # Build command()
    operating_system = get_os()
    if operating_system == 'Windows':
        cmd = f'{start}"{python_path}" "{launch_path}" '
    elif operating_system == 'Linux':
        cmd = f'{python_path} {launch_path} '
    else:
        raise UnsupportedOSException

    if 'lab_name' in config_dict:
        lab_name = config_dict['lab_name']
    else:
        lab_name = 'NO_LAB'


    cmd += f'--logip {log_ip} --logport {log_port} '
    cmd += f'--serverport {server_port} --server {server} '
    cmd += f'--device_id "{config_dict["device_id"]}" '
    cmd += f'--config {dev_config} --debug {debug} '
    cmd += f'--lab_name {lab_name}'

    if len(cmd) > 8191:
        if logger is not None:
            logger.error('Cmd too long! Server will not instantiate!')
        return
    else:
        if logger is not None:
            logger.info("Cmd len: " + str(len(cmd)))

    if ssh:
        msg_str = f'Executing command on {hostname}:\n{cmd}'
        if logger is None:
            print(msg_str)
        else:
            logger.info(msg_str)
        ssh.exec_command(cmd)
    else:
        subprocess.Popen(cmd, shell=True)

    logger.info(f"Cmd: {cmd}")

    return host_ip, server_port


def launch_script(script, config, log_ip, log_port, debug_flag, server_debug_flag, num_clients, logger=None):
    """ Launches a script

    :param script: (str) name of the script. Should be the directory in which the
        relevant script config file is located
    :param config: (str) name of the config file for the script, which specifies
        the device server info and script launching directory (and also script
        parameters, if desired)
    :param log_ip: (str) logger IP address
    :param log_port: (int) logger port number
    :param debug_flag: (bool) whether or not to debug the script/launcher
    :param server_debug_flag: (bool) whether or not to debug on the
        server-launching level
    :param num_clients: (int) total number of clients to the log server
    """

    launch_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        'launchers',
        'launcher.py'
    )

    # retrieved_client_list = logger.get_client_data()
    # logger.info(f"retrieved list = {retrieved_client_list}")

    # Build command
    operating_system = get_os()
    if operating_system == 'Windows':
        cmd = f'start "{script}_server, '
        cmd += time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
        cmd += f'" "{sys.executable}" "{launch_path}" '
    elif operating_system == 'Linux':
        cmd = f'{sys.executable} {launch_path} '
    else:
        raise UnsupportedOSException


    #logger.info(f'Script : {script}')
    #logger.info(f'config : {config}')

    config_dict = load_script_config(script, config)

    if 'lab_name' in config_dict:
        lab_name = config_dict['lab_name']
    else:
        lab_name = 'NO_LAB'

    cmd += f'--logip {log_ip} --logport {log_port} '
    cmd += f'--script {script} --num_clients {num_clients} '
    cmd += f'--config {config} --debug {debug_flag} '
    cmd += f'--server_debug {server_debug_flag}'
    cmd += f'--lab_name {lab_name}'

    if len(cmd) > 8191:
        if logger is not None:
            logger.error(f'Cmd too long! (Cmd len: {len(cmd)}) Server will not instantiate!')
        return
    else:
        if logger is not None:
            logger.info("Cmd len: " + str(len(cmd)))

    logger.info(f"cmd = {cmd}")

    subprocess.Popen(cmd, shell=True)


def get_ip():
    """ Returns a primary IP address

    :network_interface: (str) Used for Linux compatibility. Network interface of target IP address.
        Can be found out by running ifconfig.
    """

    operating_system = get_os()

    if operating_system == 'Linux':
        import netifaces as ni

    if operating_system == 'Windows':

        # Retrieve subnet from config dict
        try:
            subnet = load_config('network_configuration')['subnet']
        except:
            subnet = '140'
        ip_list = socket.gethostbyname_ex(socket.gethostname())[2]
        if len(ip_list) == 1:

            return ip_list[0]
        else:
            filtered_ip = [ip for ip in ip_list if ip.startswith(subnet)]
            if len(filtered_ip) == 0:
                return ip_list[0]
            else:
                return filtered_ip[0]

    elif operating_system == 'Linux':
        try:
            network_interface = load_config('network_config')['network_interface']
        except AttributeError:
            return socket.gethostbyname(socket.gethostname())
        import netifaces as ni
        ip = ni.ifaddresses(network_interface)[ni.AF_INET][0]['addr']
        return ip


def HDAWG_to_breakout_box(pin):
    if pin < 8 or (pin < 24 and pin >= 16):
        print("these pins are not mapped to the dio breakout box")
        return None
    else:
        if int(np.floor(pin / 4)) == 2:
            board = 0
        if int(np.floor(pin / 4)) == 3:
            board = 1
        if int(np.floor(pin / 4)) == 6:
            board = 2
        if int(np.floor(pin / 4)) == 7:
            board = 3
        channel = np.mod(pin, 4)

    return board, channel


def breakout_box_to_HDAWG(board, channel):
    if board > 4 or channel > 4:
        print("non existing board or channel for dio breakout box")
        return None
    else:
        if board == 0:
            pin = 8
        if board == 1:
            pin = 12
        if board == 2:
            pin = 24
        if board == 3:
            pin = 28

        pin = pin + channel

    return pin


def get_os():
    """Read out operating system"""

    pf = platform.system()

    if pf == 'Linux':
        operating_system = 'Linux'
    elif pf == 'Windows':
        operating_system = 'Windows'
    elif pf == "Darwin":
        operating_system = 'mac_os'
    else:
        operating_system = pf

    return operating_system


def set_graph_background(widget):
    """ Sets the background color for pyqtgraph related widgets to pylabnet style

    :param widget: base graph or legend widget
    """

    try:
        widget.getViewBox().setBackgroundColor('#19232D')

    # In case this widget does ont have a parent viewBox
    except AttributeError:
        pass

    try:
        widget.setBackground('#19232D')
    # In case this widget does ont have a parent viewBox
    except AttributeError:
        pass


class UnsupportedOSException(Exception):
    """Raised when the operating system is not supported."""
