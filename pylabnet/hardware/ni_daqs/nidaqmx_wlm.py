""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

from pylabnet.hardware.ni_daqs.nidaqmx_card import Driver, Service
from pylabnet.core.generic_server import GenericServer

# Parameters
NI_DEVICE_NAME = 'cDAQ1Mod1'


def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    ni_daqmx_logger = kwargs['logger']
    ni_driver = Driver(
        device_name=NI_DEVICE_NAME,
        logger=ni_daqmx_logger
    )

    # Instantiate server
    ni_daqmx_service = Service()
    ni_daqmx_service.assign_module(module=ni_driver)
    ni_daqmx_service.assign_logger(logger=ni_daqmx_logger)
    ni_daqmx_server = GenericServer(
        service=ni_daqmx_service,
        host='localhost',
        port=kwargs['port']
    )

    ni_daqmx_server.start()
