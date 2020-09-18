""" Launches the continuous count monitor application """

from pylabnet.launchers.launcher import Launcher
# from pylabnet.launchers.servers import si_tt
from pylabnet.scripts.counter import monitor_counts
import time

def main():

    try:
        launcher = Launcher(
            script=[monitor_counts],
            # NOTE
            #server_req=[si_tt],
            server_req=[None],
            #gui_req=['count_monitor'],
            gui_req=[None],
            params=[None]
        )
    except Exception as e:
        print(e)
        time.sleep(10)
    launcher.launch()


if __name__ == '__main__':
    main()
