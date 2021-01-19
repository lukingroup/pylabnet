from pylabnet.utils.helper_methods import load_device_config, get_ip
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.core.client_base import ClientBase

import socket
import os


class Dummy:
    pass

class Client(ClientBase):
    pass


def launch(**kwargs):
    """ Launches a dummy hardware driver and instantiates server """

    log = kwargs['logger']
    log.info(f'Launching with config {kwargs["config"]}')
    config = load_device_config(
        os.path.basename(__file__)[:-3],
        kwargs['config'],
        log
    )

    dum = Dummy()
    log.info(f'Created dummy object with configuration parameters {config}')
    dum_service = ServiceBase()
    dum_service.assign_module(module=dum)
    dum_service.assign_logger(logger=log)
    dum_server = GenericServer(
        service=dum_service,
        host=get_ip(),
        port=kwargs['port']
    )
    dum_server.start()
