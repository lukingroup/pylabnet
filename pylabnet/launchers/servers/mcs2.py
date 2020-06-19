import socket

from pylabnet.hardware.nanopositioners.smaract import MCS2
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.smaract_mcs2 import Service, Client


def launch(**kwargs):
    """ Connects to MCS2 and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    mcs2 = MCS2(logger=kwargs['logger'])
    mcs2_service = Service()
    mcs2_service.assign_module(module=mcs2)
    mcs2_service.assign_logger(logger=kwargs['logger'])
    mcs2_server = GenericServer(
        service=mcs2_service,
        host=socket.gethostbyname(socket.gethostname()),
        port=kwargs['port']
    )
    mcs2_server.start()
