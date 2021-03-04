""" Implements connection and server launching of NI-daqMX card for wavemeter locking"""

import socket
import os

from pylabnet.hardware.filterwheel.filterwheel import FW102CFilterWheel
from pylabnet.network.client_server.filterwheel import Service, Client

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
    config = load_device_config('fw102c', config, logger=kwargs['logger'])

    device_name = config['device_name']
    port_name = config['device_id']
    filters = config['filters']
    filters = {  f'{i+1}' : f'{filters[i]} OD' for i in range(len(filters))}
    filterwheel = FW102CFilterWheel(port_name=port_name, device_name=device_name, filters=filters, logger=logger)


    filterwheel_service = Service()
    filterwheel_service.assign_module(module=filterwheel)
    filterwheel_service.assign_logger(logger=logger)
    filterwheel_service_server = GenericServer(
        service=filterwheel_service,
        host=get_ip(),
        port=kwargs['port']
    )

    filterwheel_service_server.start()
