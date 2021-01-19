
from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import toptica_filterwheel1, toptica_filterwheel2
from pylabnet.scripts.filterwheels import toptica_filterwheels



def main():

    launcher = Launcher(
        script=[toptica_filterwheels],
        server_req=[toptica_filterwheel1, toptica_filterwheel2],
        gui_req=[None],
        params=[None],
        config=None
    )
    launcher.launch()


if __name__ == '__main__':
    main()
