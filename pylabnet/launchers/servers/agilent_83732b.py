from pylabnet.network.client_server.agilent_83732b import Service, Client
from pylabnet.hardware.cw_mw.agilent.ag_83732b import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('agilent_83732b', kwargs['config'])
    logger = kwargs['logger']
    ag = Driver(config_dict['device_id'], logger)

    ag_service = Service()
    ag_service.assign_module(module=ag)
    ag_service.assign_logger(logger=kwargs['logger'])
    ag_server = GenericServer(
        service=ag_service,
        host=get_ip(),
        port=kwargs['port']
    )
    ag_server.start()
