import socket

from pylabnet.utils.helper_methods import load_device_config
import pylabnet.hardware.lasers.CLD101x as laser
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.CLD101x import Service, Client


def launch(**kwargs):
    """ Connects to spectrum analyzer and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the spectrum analyzer server
    """
    config = kwargs['config']
    config = load_device_config('CLD101x', config, logger=kwargs['logger'])
    il = laser.Driver(
        gpib_address=config['device_id'],
        logger=kwargs['logger']
    )

    # Instantiate Server
    il_service = Service()
    il_service.assign_module(module=il)
    il_service.assign_logger(logger=kwargs['logger'])
    il_server = GenericServer(
        service=il_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )
    il_server.start()
