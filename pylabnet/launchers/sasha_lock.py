""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import high_finesse_ws7, nidaqmx
from pylabnet.scripts.lasers import wlm_monitor


def main():

    launcher = Launcher(
        script=[wlm_monitor],
        server_req=[high_finesse_ws7, nidaqmx],
        gui_req=['wavemeter_monitor'],
        params=[None],
        config='sasha_lock'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
