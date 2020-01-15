# Log client
from pylabnet.utils.logging.logger import LogClient

# Hardware clients
from pylabnet.hardware.wavemeter import high_finesse_ws7

# GUI client
from pylabnet.gui.pyqt import external_gui

# Script
from pylabnet.scripts.wlm_monitor import WlmMonitor

# Pause, update servers
from pylabnet.core.generic_server import GenericServer
from pylabnet.scripts.pause_script import PauseService
from pylabnet.scripts.parameter_update import UpdateService

# Connect to servers
try:
    wavemeter_client = high_finesse_ws7.Client(host='localhost', port=5678)
    wavemeter_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to wavemeter server')
try:
    gui_client = external_gui.Client(host='localhost', port=9)
    gui_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to GUI server')

# Instantiate Monitor script
wlm_monitor = WlmMonitor()
wlm_monitor.assign_wlm(wavemeter_client)
wlm_monitor.assign_gui(gui_client)

# Instantiate pause+update service & connect to logger
log_client = LogClient(
    host='localhost',
    port=1234,
    module_tag='Pause & Update'
)
update_service = UpdateService()
update_service.assign_module(module=wlm_monitor)
update_service.assign_logger(logger=log_client)
update_server = GenericServer(
    host='localhost',
    port=897,
    service=update_service
)
update_server.start()

# Set parameters
wlm_monitor.set_parameters(
    all_parameters=[
        {
            "channel": 1,
            "name": "Velocity"
        }
    ]
)
# Initialize display
wlm_monitor.initialize_channels()

# Run
wlm_monitor.run()
# import numpy as np
# print(wlm_monitor.channels[0].curve_name)
