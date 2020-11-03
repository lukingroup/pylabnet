""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.scripts.staticlines import staticline_gui_generic
from pylabnet.launchers.servers import zi_hdawg

def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[zi_hdawg],
        gui_req=[None],
        params=[None],
        config='test_config_sl'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
