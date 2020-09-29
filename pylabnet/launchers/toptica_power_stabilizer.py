""" Launches the Toptica's laser power stabilization GUI """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import nidaqmx, nidaqmx_ai
from pylabnet.scripts.lasers import laser_stabilizer


def main():

    launcher = Launcher(
        script=[laser_stabilizer],
        server_req=[nidaqmx, nidaqmx_ai],
        gui_req=[None],
        params=[None],
        config='toptica_laser_stabilization'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
