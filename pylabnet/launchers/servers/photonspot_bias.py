import pyvisa

from pylabnet.hardware.bias_box.photonspot_bias import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.photonspot_bias import Service
from pylabnet.utils.helper_methods import load_device_config, get_ip, hide_console, load_config


def launch(**kwargs):
    """ Connects to Photon Spot bias box and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    settings = load_device_config('photonspot_bias',
                                  kwargs['config'],
                                  logger=kwargs['logger']
                                  )

    serial_number = settings['device_id']
    channels = settings['channels']

    photonspot_bias_driver = Driver(
        serial_number=serial_number,
        channels=channels,
        logger=kwargs['logger'])

    photonspot_bias_service = Service()
    photonspot_bias_service.assign_module(module=photonspot_bias_driver)
    photonspot_bias_service.assign_logger(logger=kwargs['logger'])
    photonspot_bias_service_server = GenericServer(
        service=photonspot_bias_service,
        host=get_ip(),
        port=kwargs['port']
    )
    photonspot_bias_service_server.start()
