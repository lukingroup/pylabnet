from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import nidaqmx
from pylabnet.scripts.fiber_coupling import power_monitor

def main():

    launcher = Launcher(
        script=[power_monitor],
        server_req=[nidaqmx],
        gui_req=[None],
        params=[None],
        auto_connect=False,
        config='fibercoupling_b16'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
