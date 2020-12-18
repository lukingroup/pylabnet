from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import thorlabs_pm320e_front
from pylabnet.scripts.fiber_coupling import power_monitor

def main():

    launcher = Launcher(
        script=[power_monitor],
        server_req=[thorlabs_pm320e_front],
        gui_req=[None],
        params=[None],
        auto_connect=False,
        config='fiber_front'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
