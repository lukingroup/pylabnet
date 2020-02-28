# Log client
from pylabnet.utils.logging.logger import LogClient

# Hardware clients
from pylabnet.hardware.shutters.sc20shutter import Client

# GUI client
from pylabnet.gui.pyqt import external_gui

# Shutter Control Script
from pylabnet.scripts.shutter.shutter_control import ShutterControl

# Connect to servers
try:
    shutter_client = Client(host='localhost', port=5951)
    shutter_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to shutter server')
try:
    gui_client = external_gui.Client(host='localhost', port=12)
    gui_client.connect()
except ConnectionRefusedError:
    raise Exception('Cannot connect to GUI server')

# Instantiate logger used to log gui_handler log messages
log_client = LogClient(
    host='localhost',
    port=1,
    module_tag='Shuttercontrol'
)

# Instantiate shutter monitor script
shutter_monitor = ShutterControl(gui_client=gui_client, shutter_client=shutter_client, logger_client=log_client)

# Initialize buttons and run
shutter_monitor.run()


