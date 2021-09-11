""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""


from pylabnet.hardware.ni_daqs import nidaqmx_card
from pylabnet.network.client_server.nidaqmx_card import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, hide_console, load_config


def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    ni_daqmx_logger = kwargs['logger']
    try:
        ni_driver = nidaqmx_card.Driver(
            device_name=kwargs['device_id'],
            logger=ni_daqmx_logger
        )
    except AttributeError:
        try:
            config = load_config(kwargs['config'])
            ni_driver = nidaqmx_card.Driver(
                device_name=config['device'],
                logger=ni_daqmx_logger
            )
        except AttributeError:
            ni_daqmx_logger.error('Please provide valid config file')
            raise
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
        host=get_ip(),
        port=kwargs['port']
    )

    ni_daqmx_server.start()
