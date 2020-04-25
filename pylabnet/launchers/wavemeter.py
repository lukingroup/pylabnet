""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.hardware.wavemeter import high_finesse_ws7
from pylabnet.hardware.ni_daqs import nidaqmx_wlm
from pylabnet.scripts.wavemeter import wlm_monitor


def main():

    launcher = Launcher(
        script=[wlm_monitor],
        server_req=[wlm_monitor, nidaqmx_wlm],
        gui_req=['wavemeter_monitor'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
