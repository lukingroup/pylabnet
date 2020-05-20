""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import staticline_nidaqmx
from pylabnet.scripts.staticlines import staticline_gui_generic


def main():

    import ptvsd
    import os
    # 5678 is the default attach port in the VS Code debug configurations
    #self.logger.info(f"Waiting for debugger attach to PID {os.getpid()}")
    #self.logger.info(f"Waiting for debugger attach to PID {os.getpid()} (launcher_script)")
    ptvsd.enable_attach(address=('localhost', 5678))
    ptvsd.wait_for_attach()
    breakpoint()

    launcher = Launcher(
        script=[staticline_gui_generic],
        server_req=[staticline_nidaqmx],
        gui_req=['staticline_generic'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
