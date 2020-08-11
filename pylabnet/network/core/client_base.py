import rpyc
import os
from socket import timeout
from ssl import SSLError


class ClientBase:
    def __init__(self, host, port, key='pylabnet.pem'):
        """ Connects to server
        
        :param host: (str) hostname
        :param port: (int) port number
        :param key: (str) name of keyfile
        """

        # Internal vars to store server info
        self._host = ''
        self._port = 0

        # Internal vars to store refs to server
        self._connection = None
        self._service = None

        # Connect to server
        self.connect(host=host, port=port, key=key)

    def connect(self, host='place_holder', port=-1, key='pylabnet.pem'):
        """ Connects to server
        
        :param host: (str) hostname
        :param port: (int) port number
        :param key: (str) name of keyfile
        """

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
            if key is None:
                self._connection = rpyc.connect(
                    host=self._host,
                    port=self._port,
                    config={
                        'allow_public_attrs': True,
                        'sync_request_timeout': 300
                    }
                )
            else:
                key = os.path.join(os.environ['WINDIR'], 'System32', key)
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

        # Error if we attempt to make an SSL connection to an ordinary server
        except timeout:
            self._connection = None
            self._service = None
            print(
                'Tried to establish a secure SSL connection to a generic (insecure) server.\n'
                'Please try establishing an insecure client by setting key=None'
            )

        # No server running with host/port parameters
        except ConnectionRefusedError:
            self._connection = None
            self._service = None
            print(
                'Connection was refused.\n'
                f'Please check that the server is running with hostname: {host}, port: {port}'
            )
            raise

        # Error if we did not provide any key
        except ConnectionResetError:
            self._connection = None
            self._service = None
            print(
                'Failed to establish connection secure SSL server.\n'
                'Please provide a valid key'
            )

        # Failed authentication attempt
        except SSLError:
            self._connection = None
            self._service = None
            print(
                'Failed to authenticate the connection.\n'
                'Please check that you have the correct keyfile'
            )

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
