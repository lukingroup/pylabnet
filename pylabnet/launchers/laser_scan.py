""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import si_tt
from pylabnet.scripts.lasers import wlm_monitor
from pylabnet.scripts.sweeper import scan_1d


def main():

    launcher = Launcher(
        script=[scan_1d],
        server_req=[si_tt, wlm_monitor],
        gui_req=[None],
        params=[None],
        config='laser_scan'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
