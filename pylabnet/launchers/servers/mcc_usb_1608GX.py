""" Implements connection and server launching of MCC USB-1608GX DAQ"""


from pylabnet.hardware.mcc_usb_daq import mcc_usb_1608GX
from pylabnet.network.client_server.mcc_usb_1608GX import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, hide_console, load_config, load_device_config


def launch(**kwargs):
    """ Connects to MCC USB-1608GX DAQ and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    # Instantiate driver
    mcc_usb_1608GX_logger = kwargs['logger']
    try:
        config = load_device_config('mcc_usb_1608GX', kwargs['config'], logger=mcc_usb_1608GX_logger)

        mcc_usb_1608GX_driver = mcc_usb_1608GX.Driver(
            device_id=config['device_id'],
            board_number=config['board_number'],
            logger=mcc_usb_1608GX_logger
        )
    except AttributeError:
        mcc_usb_1608GX_logger.error('Please provide valid config file')
        raise
    except KeyError:
        mcc_usb_1608GX_logger.error('No device id or board_number provided. '
                                    'Please make sure proper config file is provided')
        raise

    # Instantiate server
    mcc_usb_1608GX_service = Service()
    mcc_usb_1608GX_service.assign_module(module=mcc_usb_1608GX_driver)
    mcc_usb_1608GX_service.assign_logger(logger=mcc_usb_1608GX_logger)
    mcc_usb_1608GX_server = GenericServer(
        service=mcc_usb_1608GX_service,
        host=get_ip(),
        port=kwargs['port']
    )

    mcc_usb_1608GX_server.start()
