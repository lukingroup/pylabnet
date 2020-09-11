""" Turns off toptica laser """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import toptica_dlc_pro
from pylabnet.scripts.lasers import toptica_control


def main():

    launcher = Launcher(
        script=[toptica_control],
        server_req=[toptica_dlc_pro],
        gui_req=['toptica_control'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
