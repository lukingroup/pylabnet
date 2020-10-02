""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import abstract, abstract2
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    launcher = Launcher(
        script=[staticline_gui_generic], 
        server_req=[abstract, abstract2],
        gui_req=[None],
        params=[None],
        config='test_config_sl'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
