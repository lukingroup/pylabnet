""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

import socket
import os

from pylabnet.hardware.ni_daqs import nidaqmx_card
from pylabnet.network.client_server.nidaqmx_card import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import show_console, hide_console, load_config



def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server
    Identical to nidaqmx, except uses "device" in the config file as the device name

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    ni_daqmx_logger = kwargs['logger']
    try:
        config = load_config(kwargs['config'])
        ni_driver = nidaqmx_card.Driver(
            device_name=config['device'],
            logger=ni_daqmx_logger
        )
    except AttributeError:
        config_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
            'configs'
        )
        files = [file for file in os.listdir(config_directory) if (
            os.path.isfile(os.path.join(
                config_directory, file
            )) and '.json' in file
        )]
        show_console()
        print('Available config files:\n')
        for index, file in enumerate(files):
            print(f'{index}: {file[:-5]}')
        config_index = int(input('\nPlease enter a config index: '))
        config = load_config(files[config_index][:-5], logger=ni_daqmx_logger)
        hide_console()


        ni_driver = nidaqmx_card.Driver(
            device_name=config['device'],
            logger=ni_daqmx_logger
        )
    except OSError:
        ni_daqmx_logger.error(f'Did not find NI daqMX name {config["device"]}')
        raise
    except KeyError:
        ni_daqmx_logger.error('No device name provided. '
                              'Please make sure proper config file is provided')
        raise

    # Instantiate server
    ni_daqmx_service = Service()
    ni_daqmx_service.assign_module(module=ni_driver)
    ni_daqmx_service.assign_logger(logger=ni_daqmx_logger)
    ni_daqmx_server = GenericServer(
        service=ni_daqmx_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )

    ni_daqmx_server.start()
