""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import high_finesse_ws7, toptica_dlc_pro
from pylabnet.scripts.wavemeter import wlm_monitor


def main():

    launcher = Launcher(
        script=[wlm_monitor],
        server_req=[high_finesse_ws7, toptica_dlc_pro],
        gui_req=['wavemeter_monitor'],
        params=[None],
        config='toptica_lock'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
