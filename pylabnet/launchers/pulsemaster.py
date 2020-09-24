""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import zi_hdawg
from pylabnet.scripts.pulsemaster import pulsemaster


def main():

    launcher = Launcher(
        script=[pulsemaster],
        server_req=[zi_hdawg],
        gui_req=[None],
        params=[None],
        config='pulsemaster',
        script_server=False
    )
    launcher.launch()


if __name__ == '__main__':
    main()
