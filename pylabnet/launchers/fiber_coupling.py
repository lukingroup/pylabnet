from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import thorlabs_pm320e
from pylabnet.scripts.fiber_coupling import power_monitor

launcher_settings_front = {
    'name'          : 'Fiber Front', 
    'GPIB'          : 'USB0::0x1313::0x8022::M00580034::INSTR',
    'calibration'   :  [1.112e-2]
}

launcher_settings_rear = { 
    'name'          : 'Fiber Rear', 
    'GPIB'          : 'USB0::0x1313::0x8022::M00579698::INSTR',
    'calibration'   :  [0.44]
}

def main():

    launcher = Launcher(
        script=[power_monitor],
        server_req=[thorlabs_pm320e],
        gui_req=['fiber_coupling'],
        params=[launcher_settings_front],
        auto_connect=False,
        config='fiber_front'
    )
    launcher.launch()


if __name__ == '__main__':
    main()
