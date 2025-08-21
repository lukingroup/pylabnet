from pylabnet.network.client_server.sc5521A import Service, Client
from pylabnet.hardware.cw_mw.signal_core.sc5521A import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('sc5521A', kwargs['config'])
    logger = kwargs['logger']
    sc5521A = Driver(config_dict['dll_path'], logger)

    sc5521A_service = Service()
    sc5521A_service.assign_module(module=sc5521A)
    sc5521A_service.assign_logger(logger=kwargs['logger'])
    sc5521A_server = GenericServer(
        service=sc5521A_service,
        host=get_ip(),
        port=kwargs['port']
    )
    sc5521A_server.start()
