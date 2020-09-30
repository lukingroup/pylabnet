""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import staticline_nidaqmx, abstract
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    launcher = Launcher(
        script=[staticline_gui_generic], 
        server_req=[abstract],
        gui_req=['staticline_generic'], # TODO: To be removed.
        params=[None]
        #config='config_filename' # TODO: Implement in future.
    )
    launcher.launch()


if __name__ == '__main__':
    main()
