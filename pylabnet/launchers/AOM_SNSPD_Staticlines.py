
from pylabnet.launchers.launcher import Launcher
from pylabnet.scripts.staticlines import staticline_gui_generic
from pylabnet.launchers.servers import zi_hdawg
from pylabnet.launchers.servers import nidaqmx_green
from pylabnet.launchers.servers import dio_breakout
from pylabnet.launchers.servers import nidaqmx

def main():

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[zi_hdawg, nidaqmx_green, dio_breakout, nidaqmx],
        gui_req=[None],
        params=[None],
        config='sl_config'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
