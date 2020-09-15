import socket

IMPORT_STATUS = True

try:
    import TimeTagger as TT
except ModuleNotFoundError:
    IMPORT_STATUS = False

from pylabnet.hardware.counter.swabian_instruments.time_tagger import Wrap
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.si_tt import Service, Client
from pylabnet.utils.helper_methods import load_config


def launch(**kwargs):
    """ Connects to SI TT and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    if not IMPORT_STATUS:
        msg_str = 'Please make sure Swabian Instruments drivers are installed on this machine.'
        raise ModuleNotFoundError(msg_str)

    TT.setTimeTaggerChannelNumberScheme(TT.TT_CHANNEL_NUMBER_SCHEME_ONE)

    # Connect to the device, otherwise instantiate virtual connection
    try:
        tagger = TT.createTimeTagger()
    except RuntimeError:
        kwargs['logger'].warn('Failed to connect to Swabian Instruments Time Tagger.'
                              ' Instantiating virtual device instead')
        tagger = TT.createTimeTaggerVirtual()

    try:
        config = kwargs['config']
        config = load_config(config, logger=kwargs['logger'])
    except:
        config = None

    if config is None:
        try:
            config = load_config('si_tt', logger=kwargs['logger'])
        except:
            config = {}

    for channel, trig_level in config.items():
        tagger.setTriggerLevel(int(channel)+1, float(trig_level))

    cnt_trace_wrap = Wrap(
        tagger=tagger,
        logger=kwargs['logger']
    )

    # Instantiate Server
    cnt_trace_service = Service()
    cnt_trace_service.assign_module(module=cnt_trace_wrap)
    cnt_trace_service.assign_logger(logger=kwargs['logger'])
    cnt_trace_server = GenericServer(
        service=cnt_trace_service,
        host=socket.gethostbyname_ex(socket.gethostname())[2][0],
        port=kwargs['port']
    )
    cnt_trace_server.start()
