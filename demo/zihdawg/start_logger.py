import sys
from pylabnet.utils.logging.logger import LogService
from pylabnet.core.generic_server import GenericServer
import os

if __name__ == '__main__':

    # TODO: Revert this to normal
    #host = str(sys.argv[1])
    #port = int(sys.argv[2])
    host = 'localhost'
    port = 12348

    log_service_name = 'Global Logger'
    log_folder = 'logs'

    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), log_folder)

    log_service = LogService(
        name=log_service_name,
        log_output=True,
        dir_path=dir_path,
    )

    log_service = LogService()
    log_server = GenericServer(service=log_service, host=host, port=port)
    log_server.start()

    print("Log messages will be displayed below")
