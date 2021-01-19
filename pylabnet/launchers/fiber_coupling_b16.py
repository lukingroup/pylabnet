import time

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import nidaqmx
from pylabnet.scripts.fiber_coupling import power_monitor
from pylabnet.scripts.network_setup import ssh_config


def main():

    ssh = Launcher(
        script=[ssh_config],
        server_req=[None],
        gui_req=[None],
        params=[None],
        config='fibercoupling_b16',
        script_server=False
    )
    ssh.launch()
    time.sleep(3)

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
