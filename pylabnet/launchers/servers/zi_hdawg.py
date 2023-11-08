from pylabnet.hardware.awg.zi_hdawg import Driver
from pylabnet.network.client_server.hdawg import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import load_device_config, get_ip


def launch(**kwargs):

    # Instantiate driver
    zi_logger = kwargs['logger']

    config_dict = load_device_config('zi_hdawg', kwargs['config'], logger=kwargs['logger'])

    if('device_id' in config_dict):
        device_id = config_dict['device_id']
    else:
        zi_logger.error(
            f"A device ID for the HDAWG is required! Please ensure there is a 'device_id' key-value pair in the config file."
        )
        device_id = None

    if('interface' in config_dict):
        interface = config_dict['interface'] #1GbE, USB etc.
    else:
        zi_logger.error(
            f"An interface for the HDAWG is required! Please ensure there is an 'interface' key-value pair in the config file."
        )
        interface = None

    if(interface is None or device_id is None):
        zi_logger.error(
            f"Missing required parameters in the config file. Failed to launch the zi_hdawg server."
        )
        return

    hd = Driver(device_id, interface, zi_logger)

    # Instantiate server
    hd_service = Service()
    hd_service.assign_module(module=hd)
    hd_service.assign_logger(logger=zi_logger)
    hd_server = GenericServer(
        service=hd_service,
        host=get_ip(),
        port=kwargs['port']
    )

    hd_server.start()
