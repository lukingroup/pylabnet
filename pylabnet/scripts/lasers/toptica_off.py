from pylabnet.utils.helper_methods import unpack_launcher

def launch(**kwargs):
    """ Launches the WLM monitor + lock script """

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    toptica_client = clients['toptica_dlc_pro']

    toptica_client.turn_off()
