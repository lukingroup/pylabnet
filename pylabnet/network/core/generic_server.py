import rpyc
import threading
import os


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


class SecureServer(GenericServer):

    def __init__(self, service, port, key='pylabnet.pem', host='localhost'):

        
        key = os.path.join(os.environ['WINDIR'], 'System32', key)
        
        self._server = rpyc.ThreadedServer(
            service=service,
            port=port,
            hostname=host,
            authenticator=rpyc.utils.authenticators.SSLAuthenticator(
                key, key
            )
        )

        self._server_thread = threading.Thread(
            target=self._start_server,
            args=(self._server,)
        )
