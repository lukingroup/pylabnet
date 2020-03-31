import rpyc
import traceback
import time
import socket
import pickle
import logging
import time
import os
from pylabnet.utils.helper_methods import get_dated_subdirectory

class LogHandler:
    """Protection wrapper for logger instance.

    If a module needs to log, always use this class for self.log.

    This class wraps actual logger instance into a protective layer,
    such that no errors of the logger can break the host module.
    This is necessary to avoid reducing module stability due to
    limited stability of the logger (which is often the case).

    Examples of possible errors which a logger can produce:
     - connection lost
     - no logger instance was given

    Such exceptions can break the host module. Since logging is not
    necessary for module operation, it is better to ignore them and
    do not disturb the module.
    """

    def __init__(self, logger=None):
        self._logger = None
        self.set_logger(logger=logger)

    def set_logger(self, logger):
        self._logger = logger

    def debug(self, msg_str):
        try:
            return self._logger.debug(msg_str=msg_str)
        except:
            return -1

    def info(self, msg_str):
        try:
            return self._logger.info(msg_str=msg_str)
        except:
            return -1

    def warn(self, msg_str):
        try:
            return self._logger.warn(msg_str=msg_str)
        except:
            return -1

    def error(self, msg_str):
        try:
            return self._logger.error(msg_str=msg_str)
        except:
            return -1

    def exception(self, msg_str):
        try:
            return self._logger.exception(msg_str=msg_str)
        except:
            return -1

    def critical(self, msg_str):
        try:
            return self._logger.critical(msg_str=msg_str)
        except:
            return -1


class ILog:
    pass


class LogClient:

    _level_dict = dict(
        NOLOG=100,
        CRITICAL=50,
        ERROR=40,
        WARN=30,
        INFO=20,
        DEBUG=10
    )

    def __init__(self, host, port, module_tag='', level_str='INFO'):

        # Declare all internal vars
        self._host = ''
        self._port = 0
        self._connection = None
        self._service = None
        self._level_str = ''
        self._level = 0
        self._module_tag = ''

        # Set log level
        self.set_level(level_str=level_str)

        # Set module alias to display with log messages
        self._module_tag = module_tag

        # Connect to log server
        #   This call must be performed after set_level() call:
        #       if host is None or port is None, connect() call
        #       will automatically set _level_str to 'NOLOG'
        self.connect(host=host, port=port)

        # Set module alias to display with log messages
        self._module_tag = module_tag

        # Log test message
        self.info('Started logging at {}'.format(
            time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
        ))

    def connect(self, host='place_holder', port=-1):

        # Update server address if new values are given
        if host != 'place_holder':
            self._host = host
        if port != -1:
            self._port = port

        # Clean-up old connection if it exists
        if self._connection is not None or self._service is not None:
            try:
                self._connection.close()
            except:
                pass

            self._service = None
            self._connection = None

        # Establish connection if
        if host is None or port is None:
            # 'No logging' was requested.
            #   Do not establish connection to log server and
            #   set level to 'NOLOG' to stop generating log messages
            self.set_level(level_str='NOLOG')
            return 0

        else:
            # Connect to log server
            try:
                self._connection = rpyc.connect(
                    host=self._host,
                    port=self._port,
                    config={'allow_public_attrs': True}
                )
                self._service = self._connection.root

            except Exception as exc_obj:
                self._service = None
                self._connection = None
                self._module_tag = ''

                raise exc_obj

            client_data_str = 'IP Address: {}\nTimestamp: {}'.format(
                socket.gethostbyname(socket.gethostname()),
                time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
            )

            self._service.add_client_data(self._module_tag, client_data_str)
            return 0

    def set_level(self, level_str):
        # Sanity check
        if level_str not in self._level_dict:
            return -1

        self._level_str = level_str
        self._level = self._level_dict[level_str]

        return 0

    def debug(self, msg_str):
        return self._log_msg(
            msg_str=msg_str,
            level_str='DEBUG'
        )

    def info(self, msg_str):
        return self._log_msg(
            msg_str=msg_str,
            level_str='INFO'
        )

    def warn(self, msg_str):
        return self._log_msg(
            msg_str=msg_str,
            level_str='WARN'
        )

    def error(self, msg_str):
        return self._log_msg(
            msg_str=msg_str,
            level_str='ERROR'
        )

    def exception(self, msg_str):
        # Get traceback string from the last exception
        tb_str = traceback.format_exc()

        # Prepend user-give message
        full_msg_str = msg_str + '\n' + tb_str

        return self.error(msg_str=full_msg_str)

    def critical(self, msg_str):
        return self._log_msg(
            msg_str=msg_str,
            level_str='CRITICAL'
        )

    def _log_msg(self, msg_str, level_str):

        if self._level_dict[level_str] < self._level:
            # No need to send the message
            return 0

        else:
            # ------------- To be revised -------------
            # This block depended on specific implementation if the server.
            message = '[{0}] {1}: {2}'.format(level_str, self._module_tag, msg_str)
            # Pickle message object if not just a string is sent
            # ------------- To be revised -------------

            # Try sending message to the log server
            try:
                ret_code = self._service.exposed_log_msg(
                    msg_str=message,
                    level_str=level_str
                )
                return ret_code

            # If connection was lost (EOFError)
            # or was not initialized (AttributeError),
            # try to reconnect and send the message again
            except (EOFError, AttributeError):
                # Try reconnecting.
                #   If an exception is risen at this step,
                #   one cannot fix the problem automatically and
                #   the exception should just be returned to the caller.
                #   That is why no exception catch should be done here.
                print('DEBUG: no connection. Trying to reconnect to log server')
                self.connect()

                # Try sending message again.
                #   If an exception is risen at this step,
                #   one cannot fix problem automatically and
                #   the exception should just be returned to the caller
                #   That is why no exception catch should be done here.
                print('DEBUG: Trying to resend the message')
                ret_code = self._service.exposed_log_msg(
                    msg_str=message,
                    level_str=level_str
                )
                return ret_code



class LogService(rpyc.Service):


    def __init__(self, name=None, log_file=False, directory=None, log_folder=None, form_string=None, console_level=logging.DEBUG, file_level=logging.DEBUG):
        super().__init__()

        # Note: This is inspired by https://docs.python.org/3/howto/logging-cookbook.html

        # Start instance og logging.logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(console_level)

        formatting_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' or form_string

        # create formatter
        formatter = logging.Formatter(formatting_string)

        # create file handler which logs even debug messages
        if log_file:
            filename = get_dated_subdirectory(directory, log_folder, name)
            fh = logging.FileHandler(filename)
            fh.setLevel(file_level)

            # add formatter to fh
            fh.setFormatter(formatter)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch and fh to logger
        self.logger.addHandler(ch)

        self.client_data = {}

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        # print('[LOG INFO] Client connected')
        self.logger.debug('[LOG INFO] Client connected')

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        self.logger.debug('[LOG INFO] Client disconnected')
        # print('[LOG INFO] Client disconnected')

    def exposed_log_msg(self, msg_str, level_str):
        self.logger.debug(msg_str)
        # print(msg_str)
        return 0

    def add_client_data(self, module_name, module_data):
        """ Add new client info

        :param module_name: (str) name of the module
        :param module_data: (dict) dictionary containing client data.
            e.g. {'ip_address':'0.0.0.0', 'timestamp':'2020-03-04, 12:12:12, 'data':None}
        """

        # Check if this module has already been inserted and modify its name accordingly
        mn = module_name
        module_index = 2
        while module_name in self.client_data:
            module_name = mn + str(module_index)
            module_index += 1

        # Add client data to attribute of service
        self.client_data[module_name] = module_data
        return 0
