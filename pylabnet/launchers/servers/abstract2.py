''' Configures a Staticline instance to use a NIDaqmx output'''

import socket

from pylabnet.network.client_server.abstract_device import Service, Client, Driver
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """ Connects to an abstract device.

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """
    abstract_device = Driver(logger=kwargs['logger'], init_value=2)

    abstract_service = Service()
    abstract_service.assign_module(module=abstract_device)
    abstract_service.assign_logger(logger=kwargs['logger'])
    
    abstract_service_server = GenericServer(
        service=abstract_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )

    abstract_service_server.start()
