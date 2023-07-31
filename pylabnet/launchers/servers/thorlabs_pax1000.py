import pyvisa

from pylabnet.hardware.polarization.thorlabs_pax1000 import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.thorlabs_pax1000 import Service
from pylabnet.utils.helper_methods import load_device_config, get_ip


def launch(**kwargs):
    """ Connects to thorlabs_pax1000 instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    settings = load_device_config('thorlabs_pax1000',
                                  kwargs['config'],
                                  logger=kwargs['logger']
                                  )

    dev_num = settings['device_id']

    polarimeter = Driver(logger=kwargs['logger'])

    polarimeter_service = Service()
    polarimeter_service.assign_module(module=polarimeter)
    polarimeter_service.assign_logger(logger=kwargs['logger'])
    polarimeter_service_server = GenericServer(
        service=polarimeter_service,
        host=get_ip(),
        port=kwargs['port']
    )
    polarimeter_service_server.start()
