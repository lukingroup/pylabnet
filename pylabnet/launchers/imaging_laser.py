""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import green_imaging_laser
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[green_imaging_laser],
        gui_req=['staticline_generic'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
