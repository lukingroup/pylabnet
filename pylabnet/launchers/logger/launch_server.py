import sys
import time

from pylabnet.utils.helper_methods import parse_args
from pylabnet.utils.logging.logger import LogClient

# # For debugging
# print('Waiting for debugger to connect')
# time.sleep(30)

# IMPORTANT: make sure all relevant modules are imported, otherwise you will not be able to use them via this launcher!
try:
    from pylabnet.gui.pyqt import external_gui
    from pylabnet.hardware.counter.swabian_instruments import cnt_monitor
except Exception as e:
    print('Please make sure all necessary imports are possible')
    time.sleep(20)
    raise

DEFAULT_SERVER = 'external_gui'


def main():

    # parse command line arguments
    args = parse_args()
    try:
        log_port = int(args['logport'])
    except IndexError:
        raise IndexError('Please provide command line arguments in the form\n"'
                         'python launch_gui.py --logport 1234 --serverport 5678 --server servername --module Module')
    if 'serverport' in args:
        server_port = int(args['serverport'])
    else:
        server_port = int(input('Please enter a server port value: '))
    if 'module' in args:
        module = args['module']
    else:
        module = input('Please enter a server module name: ')
    if 'server' in args:
        server = args['server']
    else:
        server = module

    # Instantiate logger
    server_logger = LogClient(
        host='localhost',
        port=log_port,
        module_tag=server+'_server',
        server_port=server_port
    )

    # Instantiate module
    try:
        mod_inst = getattr(sys.modules[__name__], module)
        mod_inst.launch(logger=server_logger, port=server_port, name=server)
    except Exception as e:
        print(module)
        print(e)
        time.sleep(15)
        raise


if __name__ == '__main__':
    main()
