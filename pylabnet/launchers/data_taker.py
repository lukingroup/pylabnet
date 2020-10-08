""" Launches the wavemeter monitor/control application """

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import si_tt, zi_hdawg, nidaqmx_green, nidaqmx
from pylabnet.scripts.lasers import wlm_monitor
from pylabnet.scripts.data_center import take_data


import time
def main():

    launcher = Launcher(
        script=[take_data],
        server_req=[si_tt, wlm_monitor, zi_hdawg, nidaqmx_green, nidaqmx],
        gui_req=[None],
        params=[None],
        config='preselected_histogram'
    )
    launcher.launch()


if __name__ == '__main__':
    main()