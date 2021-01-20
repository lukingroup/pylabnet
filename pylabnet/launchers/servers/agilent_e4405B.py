import socket

from pylabnet.utils.helper_methods import load_device_config
import pylabnet.hardware.spectrum_analyzer.agilent_e4405B as sa
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.agilent_e4405B import Service


def launch(**kwargs):
    """ Connects to spectrum analyzer and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the spectrum analyzer server
    """
    config = kwargs['config']
    config = load_device_config('agilent_e4405B', config, logger=kwargs['logger'])
    spectrum_analyzer = sa.Driver(
        gpib_address=config['device_id'],
        logger=kwargs['logger']
    )

    # Instantiate Server
    sa_service = Service()
    sa_service.assign_module(module=spectrum_analyzer)
    sa_service.assign_logger(logger=kwargs['logger'])
    sa_server = GenericServer(
        service=sa_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )
    sa_server.start()
