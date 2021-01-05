import socket

IP = 'localhost'
PORT = 49999


class WavemeterClient:
    def __init__(self, channel):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((IP, PORT))
        self.channel = channel

    def __del__(self):
        self.sock.sendall('CLOSE'.encode())
        self.sock.close()

    def read_wavelength(self):
        msg = 'WAVELENGTH {:d}'.format(self.channel)
        self.sock.sendall(msg.encode())
        res = bytes.decode(self.sock.recv(1024))
        if res != 'NONE':
            words = res.split()
            if len(words) == 2 and words[0] == 'WAVELENGTH':
                return float(words[1])
            else:
                return 0.0
        else:
            return 0.0

