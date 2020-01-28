from pylabnet.hardware.shutters.sc20shutter import SC20Shutter, Service
from pylabnet.utils.logging.logger import LogClient
from pylabnet.core.generic_server import GenericServer

# Instantiate Logger
shutter_logger = LogClient(
    host='localhost',
    port=1,
    module_tag='Shutter Log Server'
)

# Instantiate Shutter object
device_name = 'cDAQ1Mod1'
output = 'ao2'
name = 'Laser Green'

shutter = SC20Shutter(
    device_name=device_name,
    output_channel=output,
    shutter_name=name,
    logger=shutter_logger
)

# Instantiate Server
shutter_service = Service()
shutter_service.assign_module(module=shutter)
shutter_service.assign_logger(logger=shutter_logger)
shutter_service_server = GenericServer(
    service=shutter_service,
    host='localhost',
    port=5951
)

shutter_service_server.start()
