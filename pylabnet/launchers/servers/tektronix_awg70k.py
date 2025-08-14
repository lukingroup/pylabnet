""" Implements connection and server launching to a Tektronix TDS2004C oscilloscope """


from pylabnet.hardware.awg import tektronix_awg70k
from pylabnet.network.client_server.tektronix_awg70k import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip


def launch(**kwargs):
    """ Connects to Tektronix 70001B AWG and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    tektronix_logger = kwargs['logger']
    tektronix_driver = tektronix_awg70k.Driver(
        ip_address=kwargs['device_id'],
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
