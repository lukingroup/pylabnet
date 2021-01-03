from pylabnet.hardware.awg.zi_hdawg import Driver
from pylabnet.network.client_server.hdawg import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import load_device_config

import socket


def launch(**kwargs):

    # Instantiate driver
    zi_logger = kwargs['logger']

    device_id = load_device_config('zi_hdawg', kwargs['config'], logger=kwargs['logger'])['device_id']
    hd = Driver(device_id, zi_logger)

    # Instantiate server
    hd_service = Service()
    hd_service.assign_module(module=hd)
    hd_service.assign_logger(logger=zi_logger)
    hd_server = GenericServer(
        service=hd_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )

    hd_server.start()

