import socket

from pylabnet.hardware.wavemeter.high_finesse_ws7 import Driver
from pylabnet.network.client_server.high_finesse_ws7 import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip


def launch(**kwargs):
    """ Connects to HF WS7 Wavemeter and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate Logger
    wavemeter_logger = kwargs['logger']

    # Instantiate Wavemeter object
    hf_wlm = Driver(logger=wavemeter_logger)

    # Instantiate Server
    wavemeter_service = Service()
    wavemeter_service.assign_module(module=hf_wlm)
    wavemeter_service.assign_logger(logger=wavemeter_logger)
    wavemeter_server = GenericServer(
        service=wavemeter_service,
        host=get_ip(),
        port=kwargs['port']
    )

    wavemeter_server.start()
