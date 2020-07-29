import rpyc


class ClientBase:
    def __init__(self, host, port):

        # Internal vars to store server info
        self._host = ''
        self._port = 0

        # Internal vars to store refs to server
        self._connection = None
        self._service = None

        # Connect to server
        self.connect(host=host, port=port)

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

            self._connection = None
            self._service = None

        # Connect to server
        try:
            self._connection = rpyc.connect(
                host=self._host,
                port=self._port,
                config={
                    'allow_public_attrs': True,
                    'sync_request_timeout': 300
                }
            )
            self._service = self._connection.root

            return 0

        except Exception as exc_obj:
            self._connection = None
            self._service = None
            raise exc_obj

    def close_server(self):
        """ Closes the server to which the LogClient is connected"""

        try: 
            self._service.close_server()
        except EOFError:
            pass


class SecureClient(ClientBase):
    
    def connect(self, key='pylabnet.pem', host='place_holder', port=-1):

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

            self._connection = None
            self._service = None

        # Connect to server
        try:
            self._connection = rpyc.ssl_connect(
                host=self._host,
                port=self._port,
                config={
                    'allow_public_attrs': True,
                    'sync_request_timeout': 300
                },
                keyfile=key,
                certfile=key
            )
            self._service = self._connection.root

            return 0

        except Exception as exc_obj:
            self._connection = None
            self._service = None
            raise exc_obj