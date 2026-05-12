""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""


from pylabnet.hardware.lasers.TLB_6700 import Driver
from pylabnet.network.client_server.TLB_6700 import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, hide_console, load_device_config


def launch(**kwargs):
    """ Connects to Newfocus Velocity laser and launches server

    :param kwargs: (dict) containing relevant kwargs
    """

    # Instantiate driver
    velocity_logger = kwargs['logger']
    config = load_device_config('TLB_6700', kwargs['config'], velocity_logger)

    tlb = Driver(
        device_id=config['device_id'],
        New_Focus_program_path=config['New_Focus_program_path'],
        product_id=int(config['product_id']),
        logger=velocity_logger
    )

    # Instantiate server
    tlb_service = Service()
    tlb_service.assign_module(module=tlb)
    tlb_service.assign_logger(logger=velocity_logger)
    tlb_server = GenericServer(
        service=tlb_service,
        host=get_ip(),
        port=kwargs['port']
    )

    tlb_server.start()
