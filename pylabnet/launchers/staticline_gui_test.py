""" Launches the Microwave Calibration application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.hardware.staticline import staticline
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[staticline],
        gui_req=['staticline_generic'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
