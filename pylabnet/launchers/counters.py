""" Launches the continuous count monitor application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import si_tt
from pylabnet.scripts.counter import monitor_counts


def main():

    launcher = Launcher(
        script=[monitor_counts],
        server_req=[si_tt],
        gui_req=['count_monitor'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
