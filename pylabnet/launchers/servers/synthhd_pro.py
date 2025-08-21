from pylabnet.network.client_server.synthhd_pro import Service, Client
from pylabnet.hardware.cw_mw.windfreak.synthhd_pro import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('synthhd_pro', kwargs['config'])
    logger = kwargs['logger']
    synthhd_pro = Driver(config_dict['device_port'], logger)

    synthhd_service = Service()
    synthhd_service.assign_module(module=synthhd_pro)
    synthhd_service.assign_logger(logger=kwargs['logger'])
    synthhd_server = GenericServer(
        service=synthhd_service,
        host=get_ip(),
        port=kwargs['port']
    )
    synthhd_server.start()
