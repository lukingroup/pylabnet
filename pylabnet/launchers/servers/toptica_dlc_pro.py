""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

import socket
import os

from pylabnet.hardware.lasers.toptica import DLC_Pro
from pylabnet.network.client_server.toptica_dl_pro import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import show_console, hide_console, load_device_config



def launch(**kwargs):
    """ Connects to toptica laser and launches server

    :param kwargs: (dict) containing relevant kwargs
    """

    # Instantiate driver
    toptica_logger = kwargs['logger']
    config = load_device_config('toptica_dlc_pro', kwargs['config'], toptica_logger)


    dlc = DLC_Pro(
        host=config['host'], port=int(config['port']), logger=toptica_logger
    )

    # Instantiate server
    dlc_service = Service()
    dlc_service.assign_module(module=dlc)
    dlc_service.assign_logger(logger=toptica_logger)
    dlc_server = GenericServer(
        service=dlc_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )

    dlc_server.start()
