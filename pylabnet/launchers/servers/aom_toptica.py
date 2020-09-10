''' Configures a Staticline instance to use a NIDaqmx output'''

import socket

import pylabnet.hardware.awg.zi_hdawg as zi_hdawg
from pylabnet.network.client_server.staticline import Service, Client

import pylabnet.hardware.staticline.staticline as staticline


from pylabnet.network.core.generic_server import GenericServer

# Parameters
dev_id = 'dev8227'

def launch(**kwargs):
    """ Connects to a NI DAQ as staticline

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    staticline_logger = kwargs['logger']

    # Instanciate HDAWG driver.
    hd = zi_hdawg.Driver(dev_id, logger=staticline_logger)


    aom = staticline.Driver(
        name='AOM',
        logger=staticline_logger,
        hardware_module=hd,
        DIO_bit=30,
    ) 

    # Instantiate Server
    # Staticline server
    staticline_service = Service()
    staticline_service.assign_module(module=aom)
    staticline_service.assign_logger(logger=staticline_logger)
    staticline_service_server = GenericServer(
        service=staticline_service,
        host=socket.gethostbyname(socket.gethostname()),
        port=kwargs['port']
    )

    staticline_service_server.start()
