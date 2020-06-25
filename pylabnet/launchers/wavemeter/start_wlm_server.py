from pylabnet.hardware.wavemeter.high_finesse_ws7 import Driver, Service
from pylabnet.utils.logging.logger import LogClient
from pylabnet.core.generic_server import GenericServer

# Instantiate Logger
wavemeter_logger = LogClient(
    host='localhost',
    port=1234,
    module_tag='High-Finesse WS7 Wavemeter'
)

# Instantiate Wavemeter object
hf_wlm = Driver(logger=wavemeter_logger)

# Instantiate Server
wavemeter_service = Service()
wavemeter_service.assign_module(module=hf_wlm)
wavemeter_service.assign_logger(logger=wavemeter_logger)
wavemeter_server = GenericServer(
    service=wavemeter_service,
    host='localhost',
    port=5678
)

wavemeter_server.start()
