import rpyc
import traceback


class LogClient:

    _level_dict = dict(
        CRITICAL=50,
        ERROR=40,
        WARN=30,
        INFO=20,
        DEBUG=10,
        NOTSET=0
    )

    def __init__(self, port, host='localhost', module_id=None, level_str='INFO'):

        self._host = host
        self._port = port
        self._connection = None
        self._service = None
        self.connect()

        self._level_str = 'NOTSET'
        self._level = self._level_dict['NOTSET']
        self.set_level(level_str=level_str)

        self._module_id = module_id

        self.info('Started logging')

    def connect(self):
        if self._connection is not None or self._service is not None:
            try:
                self._connection.close()
            except:
                pass

            del self._service, self._connection

        try:
            self._connection = rpyc.connect(
                host=self._host,
                port=self._port,
                config={'allow_public_attrs': True}
            )
            self._service = self._connection.root
            return 0

        except:
            self._service = None
            self._connection = None

            print('[LOG ERROR] connect(): failed to establish connection')
            return -1

    def set_level(self, level_str):
        # Sanity check
        if level_str not in self._level_dict:
            return -1

        self._level_str = level_str
        self._level = self._level_dict[level_str]

        return 0

    def debug(self, msg_str):
        return self._log_msg(msg_str=msg_str, level_str='DEBUG')

    def info(self, msg_str):
        return self._log_msg(msg_str=msg_str, level_str='INFO')

    def warn(self, msg_str):
        return self._log_msg(msg_str=msg_str, level_str='WARN')

    def error(self, msg_str):
        return self._log_msg(msg_str=msg_str, level_str='ERROR')

    def exception(self, msg_str):
        tb_str = traceback.format_exc()
        full_msg_str = msg_str + '\n' + tb_str
        return self.error(msg_str=full_msg_str)

    def critical(self, msg_str):
        return self._log_msg(msg_str=msg_str, level_str='CRITICAL')

    def _log_msg(self, msg_str, level_str):

        if self._level_dict[level_str] >= self._level:

            message = f'[{level_str}] {self._module_id}: {msg_str}'

            try:
                ret_code = self._service.exposed_log_msg(
                    msg_str=message,
                    level_str=level_str
                )
                return ret_code

            # If connection was lost (EOFError) or was not initialized (AttributeError)
            except (EOFError, AttributeError):
                # try reconnecting
                print('[LOG INFO: no connection. Trying to reconnect to log server]')
                self.connect()

                try:
                    ret_code = self._service.exposed_log_msg(
                        msg_str=message,
                        level_str=level_str
                    )
                    return ret_code
                except:
                    return -1

        else:
            return 0


# class Logger:
#     pass


class LogService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        print('[LOG INFO] Client connected')

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        print('[LOG INFO] Client disconnected')

    def exposed_log_msg(self, msg_str, level_str):
        print(msg_str)
        return 0


# class LogClient:
#     def __init__(self, port, host='localhost'):
#         self._host = host
#         self._port = port
#
#         self._connection = None
#         self._service = None
#
#         self.connect()
#
#     def connect(self):
#         if self._connection is not None or self._service is not None:
#             try:
#                 self._connection.close()
#             except:
#                 pass
#
#             del self._service, self._connection
#
#         try:
#             self._connection = rpyc.connect(
#                 host=self._host,
#                 port=self._port,
#                 config={'allow_public_attrs': True}
#             )
#             self._service = self._connection.root
#             return 0
#
#         except:
#             print('[ERROR] connect(): failed to establish connection')
#             return -1
#
#     def log_msg(self, msg_str, level_str):
#         return self._service.exposed_log_msg(
#             msg_str=msg_str,
#             level_str=level_str
#         )
