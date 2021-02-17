import socket

from pylabnet.network.client_server.tp_link_hs103 import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip
from pylabnet.hardware.smart_lab.smart_plug.tp_link_hs103 import Driver
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """ Connects to TP Link HS103 Smart Plug

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :device_id: (int) Location of Smart plug (e.g. Powermeter Front Smart Plug)
    """
    settings = load_device_config('tp_link_hs103',
            kwargs['config'],
            logger=kwargs['logger']
        )


    smart_plug = Driver(
        device_id = settings['device_id'],
        logger=kwargs['logger']
    )

    # Instantiate Server
    smart_plug_service = Service()
    smart_plug_service.assign_module(module=smart_plug)
    smart_plug_service.assign_logger(logger=kwargs['logger'])
    smart_plug_server = GenericServer(
        service=smart_plug_service,
        host=get_ip(),
        port=kwargs['port']
    )
    smart_plug_server.start()
