""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import green_imaging_laser
from pylabnet.scripts.staticlines import laser_green


def main():

    launcher = Launcher(
        script=[laser_green],
        server_req=[green_imaging_laser],
        gui_req=['imaging_green'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
