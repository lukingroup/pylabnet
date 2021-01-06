from pylabnet.network.client_server.agilent_83732b import Service, Client
from pylabnet.hardware.cw_mw.agilent.ag_83732b import Driver
from pylabnet.utils.helper_methods import *


def launch(**kwargs):

    config_dict = load_device_config('agilent_83732b', kwargs['config'])
    logger = kwargs['logger']
    ag = Driver(config_dict['device_id'], logger)
    setup_full_service(
        service_class=Service,
        module=ag,
        logger=logger,
        host=get_ip()
    )
