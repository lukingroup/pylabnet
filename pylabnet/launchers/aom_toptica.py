""" Launches the staticline GUI test"""

from pylabnet.launchers.launcher import Launcher
from pylabnet.launchers.servers import aom_toptica
from pylabnet.scripts.staticlines import aom_toptica


def main():

    launcher = Launcher(
        script=[aom_toptica],
        server_req=[aom_toptica],
        gui_req=['aom_toptica'],
        params=[None]
    )
    launcher.launch()


if __name__ == '__main__':
    main()
