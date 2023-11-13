import pyvisa

from pylabnet.hardware.power_meter.newport_2936 import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.newport_2936 import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip, hide_console, load_config


def launch(**kwargs):
    """ Connects to Newport 2936 power meter and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    settings = load_device_config('newport_2936',
                                  kwargs['config'],
                                  logger=kwargs['logger']
                                  )

    device_key = settings['device_id']

    newport_2936_driver = Driver(
        device_key=device_key,
        logger=kwargs['logger'])

    newport_2936_service = Service()
    newport_2936_service.assign_module(module=newport_2936_driver)
    newport_2936_service.assign_logger(logger=kwargs['logger'])
    newport_2936_service_server = GenericServer(
        service=newport_2936_service,
        host=get_ip(),
        port=kwargs['port']
    )
    newport_2936_service_server.start()
