""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""


from pylabnet.hardware.pressure_gauge.agc_100 import AGC_100
from pylabnet.network.client_server.agc_100 import Service, Client

from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import load_config, get_ip, load_device_config


def launch(**kwargs):
    """ Connects to NI-daqMX card and launches server
    Identical to nidaqmx, except uses "device_ai" in the config file as the device name

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    logger = kwargs['logger']
    config = kwargs['config']
    config = load_device_config('agc_100', config, logger=kwargs['logger'])

    port_name = config['device_id']
    agc = AGC_100(port=port_name, logger=logger)

    agc_service = Service()
    agc_service.assign_module(module=agc)
    agc_service.assign_logger(logger=logger)
    agc__server = GenericServer(
        service=agc_service,
        host=get_ip(),
        port=kwargs['port']
    )

    agc__server.start()
