""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

import socket
import os

from pylabnet.hardware.oscilloscopes import tektronix_tds2004C
from pylabnet.network.client_server.tektronix_tds2004C import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, hide_console, load_config

def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    tektronix_logger = kwargs['logger']
    tektronix_driver = tektronix_tds2004C.Driver(
        gpib_address=kwargs['device_id'],
        logger=tektronix_logger
    )
    

    # Instantiate server
    tektronix_service = Service()
    tektronix_service.assign_module(module=tektronix_driver)
    tektronix_service.assign_logger(logger=tektronix_logger)
    tektronix_server = GenericServer(
        service=tektronix_service,
        host=get_ip(),
        port=kwargs['port']
    )

    tektronix_server.start()
