import rpyc
from pylabnet.utils.logging.logger import LogHandler


class ServiceBase(rpyc.Service):

    _module = None
    log = LogHandler()

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        self.log.info('Client connected')

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        self.log.info('Client disconnected')

    def assign_module(self, module):
        self._module = module

    def assign_logger(self, logger=None):
        self.log = LogHandler(logger=logger)
