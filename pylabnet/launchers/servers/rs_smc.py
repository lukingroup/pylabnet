
from pylabnet.network.client_server.rs_smc import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip
import pylabnet.hardware.cw_mw.rs.rs_smc as smc
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """ Connects to Rhode and Schwarz Signal Genertor and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Hittite server
    """
    config = kwargs['config']
    config = load_device_config('rs_smc', config, logger=kwargs['logger'])
    mw_source = smc.Driver(
        logger=kwargs['logger'],
        addr_str=config['device_id']
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
