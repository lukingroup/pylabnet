
# -*- coding: utf-8 -*-

"""
This file contains
"""

import numpy as np

from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.decorators.dummy_wrapper import dummy_wrap
import requests
import json


class Driver:

    def __init__(self, device_name='VVB011', IP='http://192.168.50.238', port=3, logger=None, dummy=False):
        """Instantiate NI DAQ mx card

        :device_name: (str) Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        """

        # Device name
        self.dev = device_name

        # Log
        self.log = LogHandler(logger=logger)
        self.dummy = dummy
        self.IP = IP
        self.port = str(port)

        body = {
            "code": "request",
            "cid": 4,
            "adr": "/iolinkmaster/port[" + self.port + "]/iolinkdevice/iolreadacyclic",
            "data": {"index": 16, "subindex": 0}
        }

        r0 = requests.post(IP, json=body)
        self.log.info(r0.url + ', ' + str(r0.status_code) + ', ' + r0.text)

    def response_handler(self, response, display=True):
        word_string = json.loads(response.text)['data']['value']

        # split words
        words = [word_string[2 * i:2 * i + 2] for i in range(20)]

        # assign to parameters
        v_rms = int(words[0] + words[1], 16)
        scaled_v_rms = int(words[2], 16)
        a_peak = int(words[4] + words[5], 16)
        scaled_a_peak = int(words[6], 16)
        a_rms = int(words[8] + words[9], 16)
        a_rms_scaled = int(words[10], 16)
        temperature = int(words[12] + words[13], 16)
        scaled_temperature = int(words[14], 16)
        crest = int(words[16] + words[17], 16)
        scaled_crest = int(words[18], 16)
        device_status = int(words[19][0], 16)
        out1, out2 = int(int(words[19][1], 16) / 2), int(words[19][1], 16) % 2

        if(display):
            self.log.info('v_rms: ', v_rms, '\nscaled_v_rms: ', scaled_v_rms, '\na_peak: ', a_peak, '\nscaled_a_peak: ', scaled_a_peak)
            self.log.info("a_rms: ", a_rms, '\na_rms_scaled: ', a_rms_scaled, '\ntemperature: ', temperature, '\nscaled_temperature: ', scaled_temperature)
            self.log.info('crest: ', crest, "\nscaled: ", scaled_crest, '\ndevice status: ', device_status, "\nout1, 2: ", out1, out2)
        return v_rms, a_peak, a_rms, crest

    def Request_data(self,):
        body = {
            "code": "request",
            "cid": 4711,
            "adr": "/iolinkmaster/port[" + self.port + "]/iolinkdevice/pdin/getdata"
        }
        r = requests.post(self.IP, json=body)
        return self.response_handler(r, display=False)


if __name__ == '__main__':
    vib = Driver()
    print(vib.Request_data())
