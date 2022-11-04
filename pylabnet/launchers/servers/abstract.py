import os, socket

from pylabnet.network.client_server.abstract_device import Service, Client, Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import load_device_config, get_ip

def launch(**kwargs):
    """ Connects to an abstract device.

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """
    abstract_device = Driver(logger=kwargs['logger'])

    config = load_device_config(
        os.path.basename(__file__)[:-3],
        kwargs['config'],
        kwargs['logger']
    )
    device_id = kwargs['device_id']

    abstract_service = Service()
    abstract_service.assign_module(module=abstract_device)
    abstract_service.assign_logger(logger=kwargs['logger'])

    abstract_service_server = GenericServer(
        service=abstract_service,
        host=get_ip(),
        port=kwargs['port']
    )

    abstract_service_server.start()
