from pylabnet.hardware.ni_daqs.nidaqmx_card import Driver, Service
from pylabnet.utils.logging.logger import LogClient
from pylabnet.core.generic_server import GenericServer

# Instantiate Logger
ni_daqmx_logger = LogClient(
    host='localhost',
    port=12345,
    module_tag='NI DAQmx Card'
)

# Instantiate Wavemeter object
ni_driver = Driver(
    device_name='cDAQ1Mod1',
    logger=ni_daqmx_logger
)

# Instantiate Server
ni_daqmx_service = Service()
ni_daqmx_service.assign_module(module=ni_driver)
ni_daqmx_service.assign_logger(logger=ni_daqmx_logger)
ni_daqmx_server = GenericServer(
    service=ni_daqmx_service,
    host='localhost',
    port=9912
)

ni_daqmx_server.start()
