from pylabnet.hardware.bktel import bktel
from pylabnet.network.client_server.bktel import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, load_device_config


def launch(**kwargs):
    """Connects to BKtel amplifier and launches server

    :param kwargs: (dict)
        :logger: LogClient instance
        :port:   int, server port
        :config: str, path to device config file
    """

    bktel_logger = kwargs['logger']
    try:
        config = load_device_config('bktel', kwargs['config'], logger=bktel_logger)

        # Driver now hardcodes timeouts = 1.0s. No timeout overrides here.
        bktel_driver = bktel.Driver(
            port=config['serial_port'],
            baud=config.get('baud', 9600),
            logger=bktel_logger
        )

    except AttributeError:
        bktel_logger.error('Please provide valid config file')
        raise
    except KeyError:
        bktel_logger.error('No serial_port provided. Please make sure proper config file is provided')
        raise

    bktel_service = Service()
    bktel_service.assign_module(module=bktel_driver)
    bktel_service.assign_logger(logger=bktel_logger)

    bktel_server = GenericServer(
        service=bktel_service,
        host=get_ip(),
        port=kwargs['port']
    )
    bktel_server.start()
