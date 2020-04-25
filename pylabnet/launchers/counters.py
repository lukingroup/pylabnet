import time
time.sleep(25)

""" Launches the continuous count monitor application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.hardware.counter.swabian_instruments import cnt_monitor
from pylabnet.scripts.counter import monitor_counts


def main():

    launcher = Launcher(
        script=[monitor_counts],
        server_req=[cnt_monitor],
        gui_req=['count_monitor'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
