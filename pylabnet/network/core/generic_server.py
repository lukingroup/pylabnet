import rpyc
import threading


class GenericServer:
    def __init__(self, service, port, host='localhost'):

        self._server = rpyc.ThreadedServer(
            service=service,
            hostname=host,
            port=port,
            protocol_config={
                'allow_public_attrs': True,
                'sync_request_timeout': 300
            }
        )

        self._server_thread = threading.Thread(
            target=self._start_server,
            args=(self._server,)
        )

    def start(self):
        self._server_thread.start()

    def stop(self):
        self._server.close()

    @staticmethod
    def _start_server(server_obj):
        server_obj.start()

