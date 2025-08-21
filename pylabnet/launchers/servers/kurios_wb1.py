import pyvisa

from pylabnet.hardware.adjustable_filter.kurios_wb1 import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.kurios_wb1 import Service
from pylabnet.utils.helper_methods import load_device_config, get_ip, hide_console, load_config


def launch(**kwargs):
    """ Connects to Kurios WB-1 adjustable filter and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    settings = load_device_config('kurios_wb1',
                                  kwargs['config'],
                                  logger=kwargs['logger']
                                  )

    device_addr = settings['device_id']

    kurios_wb1_driver = Driver(
        device_addr=device_addr,
        logger=kwargs['logger'])

    kurios_wb1_service = Service()
    kurios_wb1_service.assign_module(module=kurios_wb1_driver)
    kurios_wb1_service.assign_logger(logger=kwargs['logger'])
    kurios_wb1_service_server = GenericServer(
        service=kurios_wb1_service,
        host=get_ip(),
        port=kwargs['port']
    )
    kurios_wb1_service_server.start()
