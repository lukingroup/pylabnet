from pylabnet.network.client_server.synthhd import Service, Client
from pylabnet.hardware.cw_mw.windfreak.synthhd import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('synthhd', kwargs['config'])
    logger = kwargs['logger']
    synthhd = Driver(config_dict['device_port'], logger)

    synthhd_service = Service()
    synthhd_service.assign_module(module=synthhd)
    synthhd_service.assign_logger(logger=kwargs['logger'])
    synthhd_server = GenericServer(
        service=synthhd_service,
        host=get_ip(),
        port=kwargs['port']
    )
    synthhd_server.start()
