""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import staticline_nidaqmx
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[staticline_nidaqmx],
        gui_req=['staticline_generic'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
