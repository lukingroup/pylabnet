import socket
import time

from pylabnet.hardware.power_meter.thorlabs_pm320e import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.thorlabs_pm320e import Service, Client


GPIB = 'USB0::0x1313::0x8022::M00580034::INSTR'

def launch(**kwargs):
    """ Connects to PM320E and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    pm = Driver(
        logger=kwargs['logger'], 
        gpib_address=GPIB
    )
    pm_service = Service()
    pm_service.assign_module(module=pm)
    pm_service.assign_logger(logger=kwargs['logger'])
    pm_server = GenericServer(
        service=pm_service,
        host=socket.gethostbyname(socket.gethostname()),
        port=kwargs['port']
    )
    pm_server.start()
