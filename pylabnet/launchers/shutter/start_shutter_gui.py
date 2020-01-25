# Log client
from pylabnet.utils.logging.logger import LogClient

# Hardware clients
from pylabnet.hardware.shutters.sc20shutter import SC20Shutter, Client

# GUI client
from pylabnet.gui.pyqt import external_gui

# Script
from pylabnet.scripts.configurators.shutter.shutter_gui_configurator import ShutterGUIConfigurator

# Pause, update servers
from pylabnet.core.generic_server import GenericServer
from pylabnet.scripts.pause_script import PauseService
from pylabnet.scripts.parameter_update import UpdateService

# Connect to servers
try:
    shutter_client = Client(host='localhost', port=5950)
    shutter_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to wavemeter server')
try:
    gui_client = external_gui.Client(host='localhost', port=10)
    gui_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to GUI server')

# Instantiate Monitor script
shutter_monitor = ShutterGUIConfigurator()
shutter_monitor.assign_client(shutter_client)
shutter_monitor.assign_gui(gui_client)

# Instantiate pause+update service & connect to logger
log_client = LogClient(
    host='localhost',
    port=12347,
    module_tag='Pause & Update'
)
update_service = UpdateService()
update_service.assign_module(module=shutter_monitor)
update_service.assign_logger(logger=log_client)
update_server = GenericServer(
    host='localhost',
    port=897,
    service=update_service
)
update_server.start()
