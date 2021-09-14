import pyvisa

from pylabnet.hardware.polarization.thorlabs_mpc320 import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.thorlabs_mpc320 import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip, hide_console, load_config


def launch(**kwargs):
    """ Connects to MPC320 instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    settings = load_device_config('thorlabs_mpc320',
                                  kwargs['config'],
                                  logger=kwargs['logger']
                                  )

    dev_num = settings['device_id']

    pol_paddle = Driver(
        device_num=int(dev_num),
        logger=kwargs['logger'])

    pol_paddle_service = Service()
    pol_paddle_service.assign_module(module=pol_paddle)
    pol_paddle_service.assign_logger(logger=kwargs['logger'])
    pol_paddle_service_server = GenericServer(
        service=pol_paddle_service,
        host=get_ip(),
        port=kwargs['port']
    )
    pol_paddle_service_server.start()
