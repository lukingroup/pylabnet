import pylabnet.network.client_server.abstract_device as AbstractDevice
from pylabnet.network.core.generic_server import GenericServer 
from pylabnet.utils.logging.logger import LogService, LogClient

log_client = LogClient(
    host='169.254.246.113', 
    port=3250, 
    module_tag='abstract_server')

# Driver sets up the device state
abstract_driver = AbstractDevice.AbstractDriver(logger=log_client, init_value=2)

# Service will hold the device driver and will be hosted by the device server
abstract_service = AbstractDevice.AbstractService()
abstract_service.assign_module(module=abstract_driver)
abstract_service.assign_logger(logger=log_client)

abstract_server = GenericServer(
    service=abstract_service, 
    host='localhost',
    port=1234
)

abstract_server.start()