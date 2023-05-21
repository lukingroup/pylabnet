from pylabnet.network.client_server.nkt import Service, Client
from pylabnet.hardware.superK.nkt import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):
    config_dict = load_device_config('superK', kwargs['config'], kwargs['logger'])
    nkt = Driver(com_port=config_dict['com_port'],
                    devID=config_dict['devID'], 
                     logger=kwargs['logger'])

    nkt_service = Service()
    nkt_service.assign_module(module=nkt)
    nkt_service.assign_logger(logger=kwargs['logger'])
    nkt_server = GenericServer(
        service=nkt_service,
        host=get_ip(),
        port=kwargs['port']
    )
    nkt_server.start()
