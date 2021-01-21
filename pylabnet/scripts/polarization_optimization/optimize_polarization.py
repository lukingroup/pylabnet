from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import find_client, unpack_launcher, get_gui_widgets, find_client, load_script_config
from pylabnet.gui.pyqt.external_gui import Window


def launch(**kwargs):

    logger = kwargs['logger']
    clients = kwargs['clients']

    config = load_script_config(script='thorlabs_pm320e',
                            config=kwargs['config'],
                            logger=logger)


    powermeter = find_client(clients=clients, settings=config, client_type='thorlabs_pm320e')
    pol_paddle = find_client(clients=clients, settings=config, client_type='thorlabs_mpc320')