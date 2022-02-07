
from pylabnet.hardware.nanopositioners.attocube import ANC300
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.attocube_anc300 import Service, Client
from pylabnet.utils.helper_methods import get_ip, load_device_config


def launch(**kwargs):
    """ Connects to ANC3000 and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    device_config = load_device_config('anc300', kwargs['config'], logger=kwargs['logger'])
    telnet_config = device_config['telnet_config']


    anc300 = ANC300(
        host=telnet_config['host'], 
        port=telnet_config['port'], 
        query_delay=device_config['query_delay'], 
        passwd=telnet_config['passwd'], 
        limits = device_config['limits'],
        logger=kwargs['logger']
    )


    anc300_service = Service()
    anc300_service.assign_module(module=anc300)
    anc300_service.assign_logger(logger=kwargs['logger'])
    anc300_server = GenericServer(
        service=anc300_service,
        host=get_ip(),
        port=kwargs['port']
    )
    anc300_server.start()
