""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.scripts.pulsemaster import pulsemaster


def main():

    launcher = Launcher(
        script=[pulsemaster],
        server_req=[None],
        gui_req=[None],
        params=[None],
        config='pulsemaster',
        script_server=True
    )
    launcher.launch()


if __name__ == '__main__':
    main()
