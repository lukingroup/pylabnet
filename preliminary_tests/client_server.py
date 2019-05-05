import rpyc
import threading


class Server:
    def __init__(self, module_service, port, host='localhost'):

        self._server = rpyc.ThreadedServer(
            service=module_service,
            hostname=host,
            port=port,
            protocol_config=rpyc.core.protocol.DEFAULT_CONFIG
        )

        self._server_thread = threading.Thread(
            target=self._start_server,
            args=(self._server,)
        )

    @staticmethod
    def _start_server(server_obj):
        server_obj.start()

    def start(self):
        self._server_thread.start()

    def stop(self):
        pass


class ModuleService(rpyc.Service):

    module_ref = None

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def assign_module(self, module_ref):
        self.module_ref = module_ref


class Client:

    def __init__(self, port, host='localhost'):
        self._connection = rpyc.connect(
            host=host,
            port=port,
            config={'allow_public_attrs': True}
        )
        self._module_ref = self._connection.root.module_ref

    def get_module(self):
        return self._module_ref

