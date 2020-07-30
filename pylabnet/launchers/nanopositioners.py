
from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import mcs2
from pylabnet.scripts.fiber_coupling import mcs2_control


def main():

    launcher = Launcher(
        script=[mcs2_control],
        server_req=[mcs2],
        gui_req=['positioner_control'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
