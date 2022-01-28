""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, hide_console, load_device_config
import pylabnet.hardware.ifm.vvb011 as vvb011
from pylabnet.network.client_server.ifm import Service, Client

def launch(**kwargs):
    """ Connects to toptica laser and launches server

    :param kwargs: (dict) containing relevant kwargs
    """

    # Instantiate driver
    vib_logger = kwargs['logger']
    config = load_device_config('ifm', kwargs['config'], vib_logger)

    vib = vvb011.Driver(
        host=config['host'], port=int(config['port']), logger=vib_logger
    )

    # Instantiate server
    ifm_service = Service()
    ifm_service.assign_module(module=vib)
    ifm_service.assign_logger(logger=vib_logger)
    ifm_service_server = GenericServer(
        service=ifm_service, 
        host=get_ip(),
        port=kwargs['port']
    )

    ifm_service_server.start()


