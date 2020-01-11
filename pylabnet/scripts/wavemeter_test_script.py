from pylabnet.hardware.wavemeter.high_finesse_ws7 import Driver
from pylabnet.scripts.wlm_monitor import WlmMonitor

wlm_hardware = Driver()
wlm_monitor = WlmMonitor(wlm_client = wlm_hardware)
wlm_monitor.set_params(
    channels=[
        {"channel": 1,
         "setpoint": 407.067975,
         "lock": True,
         "PID": [1, 1, 0]
        }
    ],
    update_rate=0.1,
    display_pts=500,
    bin_by=1
)
wlm_monitor.run()
