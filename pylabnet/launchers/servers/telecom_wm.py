
from pylabnet.hardware.wavemeter.telecom_wm import Driver
from pylabnet.network.client_server.high_finesse_ws7 import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import load_device_config, get_ip


def launch(**kwargs):
    """ Connects to Telecom Wavemeter and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate Logger
    wavemeter_logger = kwargs['logger']

    gpib_addr = load_device_config('telecom_wm', kwargs['config'], logger=kwargs['logger'])['gpib_addr']

    # Instantiate Wavemeter object
    telecom_wm = Driver(gpib_addr, logger=wavemeter_logger)

    # Instantiate Server
    wavemeter_service = Service()
    wavemeter_service.assign_module(module=telecom_wm)
    wavemeter_service.assign_logger(logger=wavemeter_logger)
    wavemeter_server = GenericServer(
        service=wavemeter_service,
        host=get_ip(),
        port=kwargs['port']
    )

    wavemeter_server.start()
