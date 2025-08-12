from pylabnet.network.client_server.agiltron_ffsw import Service, Client
from pylabnet.hardware.fiber_switch.agiltron_ffsw import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('agiltron_ffsw', kwargs['config'])
    logger = kwargs['logger']
    device = Driver(device_id=config_dict['device_id'],
                    num_chs=config_dict['num_chs'],
                    logger=logger)

    service = Service()
    service.assign_module(module=device)
    service.assign_logger(logger=kwargs['logger'])
    server = GenericServer(
        service=service,
        host=get_ip(),
        port=kwargs['port']
    )
    server.start()
