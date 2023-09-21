""" Base module for servers in pylabnet

`GenericServer` creates an `rpyc.ThreadedServer` and assigns it a service (should be an instance
of `ServiceBase` class), which exposes functionality to clients that connect to the server. The
`GenericServer` can be identified and accessed via a `hostname` (IP address, or `'localhost'` if
local) and `port` number from 0 to 65535 (recommended to use ports 1024 to 49151). For a generic
(insecure) connection without authentication, the `key` parameter can be set to `None`.

The connection can be made secure by passing the name of a valid self-signed key file in the
C:/Windows/System32 directory. This can be generated using the OpenSSL toolkit from the commandline
using the command
```bash
openssl req -new -x509 -days -365 -nodes -out my_key.pem -keyout my_key.pem
```
which generates a keyfile automatically in C:/Windows/System32 named my_key.pm that is valid for
365 days.

NOTE: this module defaults to using a key as described above. If you would like to run the
software without authentication, change the default value to key=None here and in ClientBase
"""


import rpyc
import threading
import os
import platform


class GenericServer:
    def __init__(self, service, host, port, key='pylabnet.pem'):
        """ Instantiates a server

        :param service: ServiceBase instance to assign to server
        :param host: (str) name of host (can use 'localhost' for local connections)
        :param port: (int) port number to use - must be unique
        :param key: (str, optional) name of key file stored in C:/Windows/System32/ (for windows, /etc/ssl/certs for linux)
            for authentication purposes. If None, a standard server (without secure
            authentication) will be used
        """

        self.operating_system = get_os()
        if key is None:

            # start a server without any authentication
            self._server = rpyc.ThreadedServer(
                service=service,
                hostname=host,
                port=port,
                protocol_config={
                    'allow_public_attrs': True,
                    'sync_request_timeout': 300
                }
            )

        else:

            # identify key
            if self.operating_system == "Windows":
                key = os.path.join(os.environ['WINDIR'], 'System32', key)
            elif self.operating_system == "Linux":
                key = os.path.join('/etc/ssl/certs', 'pylabnet.pem')

            if os.path.exists(key):

                # Add SSL authentication
                self._server = rpyc.ThreadedServer(
                    service=service,
                    hostname=host,
                    port=port,
                    protocol_config={
                        'allow_public_attrs': True,
                        'sync_request_timeout': 300
                    },
                    authenticator=rpyc.utils.authenticators.SSLAuthenticator(
                        key, key
                    )
                )

            else:
                msg_str = f'\nNo keyfile found, please check that {key} exists.\n'
                print(msg_str)
                raise FileNotFoundError(msg_str)

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


def get_os():
    """Read out operating system"""

    pf = platform.system()

    if pf == 'Linux':
        operating_system = 'Linux'
    elif pf == 'Windows':
        operating_system = 'Windows'
    elif pf == "Darwin":
        operating_system = 'mac_os'
    else:
        operating_system = pf

    return operating_system
