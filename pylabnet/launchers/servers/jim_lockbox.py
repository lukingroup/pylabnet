from pylabnet.network.client_server.jim_lockbox import Service, Client
from pylabnet.hardware.lockbox.jim_lockbox import Driver
from pylabnet.utils.helper_methods import GenericServer, get_ip, load_device_config


def launch(**kwargs):

    config_dict = load_device_config('jim_lockbox', kwargs['config'], kwargs['logger'])
    lockbox = Driver(com_port=config_dict['device_id'],
                     baudrate=config_dict['baudrate'],
                     timeout=config_dict['timeout'],
                     logger=kwargs['logger'])

    lockbox_service = Service()
    lockbox_service.assign_module(module=lockbox)
    lockbox_service.assign_logger(logger=kwargs['logger'])
    lockbox_server = GenericServer(
        service=lockbox_service,
        host=get_ip(),
        port=kwargs['port']
    )
    lockbox_server.start()
