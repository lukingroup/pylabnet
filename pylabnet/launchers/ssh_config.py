""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.scripts.network_setup import ssh_config



def main():

    launcher = Launcher(
        script=[ssh_config],
        server_req=[None],
        gui_req=[None],
        params=[None],
        config='ssh_config',
        script_server=False
    )
    launcher.launch()


if __name__ == '__main__':
    main()
