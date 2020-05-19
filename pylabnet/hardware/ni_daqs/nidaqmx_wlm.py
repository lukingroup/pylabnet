""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

from pylabnet.hardware.ni_daqs import nidaqmx_card
from pylabnet.network.core.generic_server import GenericServer

# Parameters
NI_DEVICE_NAME = 'cDAQ1Mod1'


class Client(nidaqmx_card.Client):
    pass


def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    ni_daqmx_logger = kwargs['logger']
    try:
        ni_driver = nidaqmx_card.Driver(
            device_name=NI_DEVICE_NAME,
            logger=ni_daqmx_logger
        )
    except OSError:
        ni_daqmx_logger.error(f'Did not find NI daqMX name {NI_DEVICE_NAME}')
        raise

    # Instantiate server
    ni_daqmx_service = nidaqmx_card.Service()
    ni_daqmx_service.assign_module(module=ni_driver)
    ni_daqmx_service.assign_logger(logger=ni_daqmx_logger)
    ni_daqmx_server = GenericServer(
        service=ni_daqmx_service,
        host='localhost',
        port=kwargs['port']
    )

    ni_daqmx_server.start()
