""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.scripts.staticlines import staticline_gui_generic
from pylabnet.launchers.servers import zi_hdawg
from pylabnet.launchers.servers import nidaqmx_green
from pylabnet.launchers.servers import dio_breakout

def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[zi_hdawg, nidaqmx_green, dio_breakout],
        gui_req=[None],
        params=[None],
        config='test_config_sl'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
