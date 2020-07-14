from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import thorlabs_pm320e
from pylabnet.scripts.fiber_coupling import power_monitor


def main():

    launcher = Launcher(
        script=[power_monitor],
        server_req=[thorlabs_pm320e],
        gui_req=['fiber_coupling'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
