# Smarak Maity 2018-12-15

import socket
import json
import struct
from pylabnet.utils.helper_methods import (load_config, find_client, load_script_config)
from pylabnet.utils.logging.logger import LogClient, LogHandler


class MSquaredWMServer:
    """ Server exposing the High Finesse Wave Meter to the M2 SolsTis control interface

    :ip: (str) IP adress the M2 interface is listening for a wavemeter connection
        (must be set accordingly in web interface).
    :port: (int) Port number the M2 interface is listening for a wavemeter connection
        (must be set accordingly in web interface) .
    :channel: (int) Wavemeter channel where SolTis is connected to.
    :log_client: (object) LogClient instance.
    :wavemeterclient: (object) Wavemeter client instance.
    :log_tcp: (bool) If True, log incoming and outgoing TCP packets.
    """
    def __init__(self, ip, port, channel, log_client, wavemeterclient, log_tcp):
        self.ip = ip
        self.port = port
        self.log_tcp = log_tcp
        self.log = LogHandler(log_client)
        self.channel = channel
        self.trans_id = 512193
        self.wm = wavemeterclient

    def read_wavelength(self):
        return self.wm.get_wavelength(channel=self.channel, units="Wavelength (nm)")

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (self.ip, self.port)
        self.sock.bind(self.addr)
        self.sock.listen(1)
        self.log.info(f"Started server on {self.addr}")
        self.log.info(f"Initial wavelength {self.read_wavelength()}")
        self.loop()

    def loop(self):
        while True:
            conn, c_addr = self.sock.accept()
            try:
                self.log.info(f"Connection from {c_addr}")
                while True:
                    msg = conn.recv(1024)
                    if msg:
                        if self.log_tcp:
                            self.log.info(f"Recieved\n {msg} \n")
                        res = self.response(msg)
                        conn.sendall(res)
                        if self.log_tcp:
                            self.log.info(f"Sent\n {res} \n")
                    else:
                        break
            finally:
                conn.close()

    def response(self, msg):
        data = json.loads(msg)
        task = data['message']['transmission']['task1']['name']
        res = self.default_data()
        self.set_id(res, self.trans_id)
        self.trans_id += 1
        if task == 'start-link':
            self.set_task_name(res, 'start-link-reply')
            params = {
                'status': 'ok',
                'ip-address': self.ip
            }
            self.set_task_params(res, params)
        elif task == 'get-wavelength':
            self.set_task_name(res, 'get-wavelength-reply')
            params = {
                'status': 'ok',
                'wavelength': [self.read_wavelength()],
                'mode': 'fixed',
                'channel': [self.channel],
                'calibration': 'inactive',
                'configuration': 'ok'
            }
            self.set_task_params(res, params)
        elif task == 'wlm-server-app':
            self.set_task_name(res, 'wlm-server-app-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'ok',
            }
            self.set_task_params(res, params)
        elif task == 'check-wlm-server':
            self.set_task_name(res, 'check-wlm-server-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'active',
            }
            self.set_task_params(res, params)
        elif task == 'configure-wlm':
            self.set_task_name(res, 'configure-wlm-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'result-mode': 'ok',
                'exposure-mode': 'ok',
                'pulse-mode': 'ok',
                'precision': 'ok',
                'fast-mode': 'ok',
                'pid-p': 'failed',
                'pid-i': 'failed',
                'pid-d': 'failed',
                'pid-t': 'failed',
                'pid-dt': 'failed',
                'sensitivity-factor': 'failed',
                'use-ta': 'failed',
                'polarity': 'failed',
                'sensitivity-dimension': 'failed',
                'use-const-dt': 'failed',
                'auto-clear-history': 'failed'
            }
            self.set_task_params(res, params)
        elif task == 'set-measurement-op':
            self.set_task_name(res, 'set-measurement-op-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'ok'
            }
            self.set_task_params(res, params)
        elif task == 'set-switch':
            self.set_task_name(res, 'set-switch-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'ok'
            }
            self.set_task_params(res, params)
        elif task == 'set-exposure':
            self.set_task_name(res, 'set-exposure-reply')
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'ok'
            }
            self.set_task_params(res, params)

        # If unhandled task, just add generic status:ok reply
        else:
            reply_task = f'{task}-reply'
            self.set_task_name(res, reply_task)
            self.set_task_id(res, self.get_task_id(data))
            params = {
                'status': 'ok'
            }
            self.set_task_params(res, params)

        return json.dumps(res).encode('ascii')

    def set_id(self, data, i):
        data['message']['transmission-id'] = [i]

    def set_task_name(self, data, name):
        data['message']['transmission']['task1']['name'] = name

    def get_task_id(self, data):
        return data['message']['transmission']['task1']['id'][0]

    def set_task_id(self, data, i):
        data['message']['transmission']['task1']['id'] = [i]

    def set_task_params(self, data, params):
        data['message']['transmission']['task1']['parameters'] = params

    def default_data(self):
        data = {
            'message': {
                'transmission-id': [0],
                'task-count': [1],
                'transmission': {
                    'task1': {
                        'name': '',
                        'id': [1],
                        'parameters': {
                        }
                    }
                }
            }
        }
        return data

def launch(**kwargs):
    logger = kwargs['logger']

    clients = kwargs['clients']
    config = load_script_config(script='m2_laserscan',
                                config=kwargs['config'],
                                logger=logger)

    channel, ip, port, log_tcp = config['channel'], config['ip'], config['port'], config["log_tcp_packets"]

    wavemeter_client = find_client(
        clients=clients,
        settings=config,
        client_type='high_finesse_ws7',
        logger=logger
    )

    server = MSquaredWMServer(ip, port, channel, logger, wavemeter_client, log_tcp)
    server.start()



