from pylabnet.network.client_server.siglent_sdg6032x import Service, Client
from pylabnet.hardware.cw_mw.siglent.sdg_6032x import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('siglent_sdg6032x', kwargs['config'])
    logger = kwargs['logger']
    device = Driver(device_id=config_dict['device_id'], logger=logger)

    service = Service()
    service.assign_module(module=device)
    service.assign_logger(logger=kwargs['logger'])
    server = GenericServer(
        service=service,
        host=get_ip(),
        port=kwargs['port']
    )
    server.start()
