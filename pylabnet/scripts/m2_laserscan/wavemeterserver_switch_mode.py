import socket
import ctypes
import time
from threading import Thread, Lock


from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.helper_methods import (load_config, find_client, load_script_config)
from pylabnet.utils.logging.logger import LogClient, LogHandler




IP = 'localhost'
PORT = 49999
# minimum is about 0.15 s
SLEEP = 0.2


class Wavemeter():
    def __init__(self, wavemeterclient):
        self.wm = wavemeterclient

    def read_wavelength(self, channel):
        return self.wm.get_wavelength(channel=channel, units="Wavelength (nm)")


class ClientThread(Thread):
    def __init__(self, csock, caddr, wavemeter):
        Thread.__init__(self)
        self.csock = csock
        self.caddr = caddr
        self.wavemeter = wavemeter

    def run(self):
        print('Started thread for client {}'.format(self.caddr))
        while True:
            msg = self.csock.recv(1024)
            if msg:
                print('Recieved {}'.format(msg))
                res = self.response(bytes.decode(msg))
                if res == 'CLOSE':
                    print('Exiting thread for client {}'.format(self.caddr))
                    break
                self.csock.sendall(res.encode())
                print('Sent {}'.format(res))
            else:
                continue

    def response(self, msg):
        words = msg.split()
        if len(words) == 2 and words[0] == 'WAVELENGTH':
            channel = int(words[1])
            if (channel > 0) and (channel < 5):
                wavelength = self.wavemeter.read_wavelength(channel)
                return 'WAVELENGTH {:f}'.format(wavelength)
            else:
                return 'NONE'
        elif len(words) == 1 and words[0] == 'CLOSE':
            return 'CLOSE'
        else:
            return 'NONE'


class WavemeterServer:
    def __init__(self, log_client, wavemeterclient):
        self.log = LogHandler(log_client)
        self.wavemeter = Wavemeter(wavemeterclient)

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (IP, PORT)
        self.sock.bind(self.addr)
        self.sock.listen(1)
        self.log.info(f"Started wavemeter server on {self.addr}")
        self.loop()

    def loop(self):
        while True:
            (csock, caddr) = self.sock.accept()
            cthread = ClientThread(csock, caddr, self.wavemeter)
            cthread.start()

def launch(**kwargs):

    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(script='m2_server',
                                config=kwargs['config'],
                                logger=logger)


    wavemeter_client = find_client(
        clients=kwargs['clients'],
        settings=config,
        client_type='high_finesse_ws7',
        logger=logger
    )

    server = WavemeterServer(logger, wavemeter_client)
    server.start()
