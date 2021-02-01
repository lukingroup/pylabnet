import socket

from pylabnet.network.client_server.HMC_T2220 import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip
import pylabnet.hardware.cw_mw.hittite.HMC_T2220 as ht
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """ Connects to HWC T2220 (microwave source) and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Hittite server
    """
    config = kwargs['config']
    config = load_device_config('HMC_T2220', config, logger=kwargs['logger'])
    mw_source = ht.Driver(
        logger=kwargs['logger'],
        gpib_address=config['device_id']
    )

    # Instantiate Server
    mw_service = Service()
    mw_service.assign_module(module=mw_source)
    mw_service.assign_logger(logger=kwargs['logger'])
    mw_server = GenericServer(
        service=mw_service,
        host=get_ip(),
        port=kwargs['port']
    )
    mw_server.start()
