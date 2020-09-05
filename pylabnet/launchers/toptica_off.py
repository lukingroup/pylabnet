""" Turns off toptica laser """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import toptica_dlc_pro
from pylabnet.scripts.lasers import toptica_off


def main():

    launcher = Launcher(
        script=[toptica_off],
        server_req=[toptica_dlc_pro],
        gui_req=[],
        params=[None],
        config='toptica_lock',
        script_server=False
    )
    launcher.launch()


if __name__ == '__main__':
    main()
