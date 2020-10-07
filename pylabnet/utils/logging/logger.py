import rpyc
import traceback
import time
import socket
import logging
import sys
import os
import ctypes
import re
import pickle
from pylabnet.utils.helper_methods import get_dated_subdirectory_filepath


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
            self._logger.error(msg_str=msg_str)
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

    def update_data(self, data):
        try:
            return self._logger.update_data(data)
        except:
            return -1

    def update_metadata(self, **metadata):
        """ Updates experiment-related metadata

        :param metadata: (dict) dictionary containing relevant metadata
        """
        try:
            return self._logger.update_metadata(**metadata)
        except:
            return -1
    
    def get_metadata(self):
        """ Returns all metadata"""

        try:
            return self._logger.get_metadata()
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

    def __init__(self, host, port, key='pylabnet.pem', module_tag='', server_port=None, ui=None):

        # Declare all internal vars
        self._host = ''
        self._port = 0
        self._connection = None
        self._service = None
        self._level_str = ''
        self._level = 0
        self._module_tag = ''
        self._server_port = server_port  # Identifies a server running in client's thread
        self._ui = ui  # Identifies a relevant .ui file for the client

        # Set module alias to display with log messages
        self._module_tag = module_tag

        # Connect to log server
        self.connect(host=host, port=port, key=key)

        # Set module alias to display with log messages
        self._module_tag = module_tag

        # Log test message
        self.info('Started logging')

    def connect(self, host='place_holder', port=-1, key='pylabnet.pem'):

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
            #   Do not establish connection to log server
            return 0

        else:
            # Connect to log server
            try:
                if key is None:
                    self._connection = rpyc.connect(
                        host=self._host,
                        port=self._port,
                        config={'allow_public_attrs': True}
                    )
                else:
                    key = os.path.join(os.environ['WINDIR'], 'System32', key)
                    self._connection = rpyc.ssl_connect(
                        host=self._host,
                        port=self._port,
                        config={'allow_public_attrs': True},
                        keyfile=key,
                        certfile=key
                    )
                self._service = self._connection.root

            except Exception as exc_obj:
                self._service = None
                self._connection = None
                self._module_tag = ''

                raise exc_obj

            client_data = dict(
                ip=socket.gethostbyname_ex(socket.gethostname())[2][0],
                timestamp=time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime())
            )
            if self._server_port is not None:
                client_data['port'] = self._server_port
            if self._ui is not None:
                client_data['ui'] = self._ui

            client_data_pickle = pickle.dumps(client_data)
            self._service.add_client_data(self._module_tag, client_data_pickle)
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

    def update_data(self, data=None):
        """ Updates client data with new information

        :param data: (dict) containing client data
            e.g. {'port': 4444, 'other-data': XYZ}
        """

        if data is not None:
            client_data_pickle = pickle.dumps(data)
            self._service.update_client_data(self._module_tag, client_data_pickle)

    def _log_msg(self, msg_str, level_str):

        # Prepending log message with module name.
        message = ' {0}: {1}'.format(self._module_tag, msg_str)

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

    def close_server(self):
        """ Closes the server to which the LogClient is connected"""

        try:
            self._service.close_server()
        except EOFError:
            pass

    def update_metadata(self, **metadata):
        """ Updates experiment-related metadata

        :param metadata: (dict) dictionary containing relevant metadata
        """

        self._service.exposed_update_metadata(pickle.dumps(metadata))

    def get_metadata(self):
        """ Returns all metadata"""

        return pickle.loads(self._service.exposed_get_metadata())


class LogService(rpyc.Service):

    def __init__(self, form_string=None, console_level=logging.DEBUG, file_level=logging.DEBUG, log_output=False,
                 name=None, dir_path=None):
        """ Instantiate LogService

        If the log_output flag is set to True, a .log file will be generated.

        :form_string: String specifying the output format of the logger. If None, default styling is:
            "%(asctime)s - %(levelname)s - %(message)s"
        :console_level: The minimum message level which appears in the console.
        :file_level: The minimum message level which appears in the log-file.
        :log_output: Boolean indicating if a file output should be generated. If true, the following
            two parameters must be provided:
        :name: Name of the log-file.
        :dir_path: Directory where the log files will be generated.

        Note: A dated subdirectory structure will be automatically generated, such that the
        log output will be logged in the following file:
            'dir_path/YEAR/MONTH/DAY/name.log'
        """

        super().__init__()

        # Note: This is inspired by https://docs.python.org/3/howto/logging-cookbook.html

        # Start instance og logging.logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(console_level)

        formatting_string = '%(asctime)s - %(levelname)s - %(message)s' or form_string

        # create formatter
        formatter = logging.Formatter(formatting_string)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(ch)

        # create file handler which logs even debug messages
        if log_output:

            assert name, 'Please provide a name for the logger.'
            assert dir_path, 'Please provide a directory path for the .log file.'

            filename = get_dated_subdirectory_filepath(dir_path, name)
            fh = logging.FileHandler(filename)
            fh.setLevel(file_level)

            # add formatter to fh
            fh.setFormatter(formatter)

            # add fh to logger
            self.logger.addHandler(fh)

        self.client_data = {}
        self.metadata = {}
        self.data_updated = []  # Identifies which clients have updated data

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        self.logger.info('Client connected')

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        self.logger.debug('Client disconnected')

    def exposed_log_msg(self, msg_str, level_str):

        if level_str == 'DEBUG':
            self.logger.debug(msg_str)

        elif level_str == 'INFO':
            self.logger.info(msg_str)

        elif level_str == 'WARN':
            self.logger.warning(msg_str)

        elif level_str == 'ERROR':
            self.logger.error(msg_str)

        return 0

    def add_client_data(self, module_name, module_data_pickle):
        """ Add new client info

        :param module_name: (str) name of the module
        :param module_data_pickle: (pickle) pickled dictionary containing client data.
            e.g. {'ip_address':'0.0.0.0', 'timestamp':'2020-03-04, 12:12:12, 'data':None}
        """

        # Check if this module has already been inserted and modify its name accordingly
        mn = module_name
        module_index = 2
        while module_name in self.client_data:
            module_name = mn + str(module_index)
            module_index += 1

        # Add client data to attribute of service
        self.client_data[module_name] = pickle.loads(module_data_pickle)
        return 0

    def update_client_data(self, module_name, module_data_pickle):
        """ Update client info

        :param module_name: (str) name of module
        :param module_data_pickle: (pickle) pickled dictionary containing client data.
            e.g. {'port': 4444, 'other-data': XYZ}
        """

        try:
            # Check for module name copies in client data
            matches = []
            indices = []
            pattern = re.compile(f'^{module_name}\d')
            for module in self.client_data:
                if re.match(pattern, module):
                    matches.append(module)
                    indices.append(int(module[-1]))

            if len(matches) > 0:
                module_name = matches[indices.index(max(indices))]

            self.client_data[module_name].update(pickle.loads(module_data_pickle))
            # self.logger.info('Updated client data for {}'.format(module_name))
            self.data_updated.append(module_name)
        except IndexError:
            self.logger.warning('Tried to update client data for {}, but could not find it in list of clients!'.format(
                module_name
            ))

    def close_server(self):
        """ Closes the server for which the service is running """

        pid = os.getpid()
        handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)

    def add_logfile(self, name, dir_path, file_level=logging.DEBUG, form_string=None):
        """ Adds a log-file for all future logging

        :name: Name of the log-file.
        :dir_path: Directory where the log files will be generated.
        :file_level: The minimum message level which appears in the log-file.
        :form_string: String specifying the output format of the logger. If None, default styling is:
            "%(asctime)s - %(levelname)s - %(message)s"
        """

        formatting_string = '%(asctime)s - %(levelname)s - %(message)s' or form_string
        formatter = logging.Formatter(formatting_string)
        filename = get_dated_subdirectory_filepath(dir_path, name)
        fh = logging.FileHandler(filename)
        fh.setLevel(file_level)

        # add formatter to fh
        fh.setFormatter(formatter)

        # add fh to logger
        self.logger.addHandler(fh)

    def stop_latest_logfile(self):
        """ Stops the latest logfile """

        self.logger.removeHandler(self.logger.handlers[-1])

    def exposed_update_metadata(self, metadata):
        """ Updates metadata """

        self.metadata.update(pickle.loads(metadata))
        self.logger.info('Metadata updated')
    
    def exposed_get_metadata(self):
        """ Returns all client metadata"""

        return pickle.dumps(self.metadata)
