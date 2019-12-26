# -*- coding: utf-8 -*-

from pylabnet.hardware.ni_daqs.nidaqmx_card import Ni_Daq_Mx_Card
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


"""
This file contains the pylabnet Hardware module class for SDC20 Thorlabs shutter.

The shutter is triggered via a 5V TTL signal from a NI DAQmx card

"""

class SC20Shutter():

    def __init__(self, device_name, output_channel, shutter_name, logger=None):
        """Instantiate Harware class for SC20 Thorlabs by instanciating NI DAQ card an assiging channel

        :device_name: Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        :ao_channel: Name of output channel where SC20 is connected(e.g. 'ao1', 'ao2')
        :shutter_name: Readable name of shutter (e.g. 'Collection Path') 
        """
        # Retrieve member variables 
        self.device_name = device_name
        self.output_channel = output_channel
        self.shutter_name = shutter_name

        # Instanciate NI DAQ
        self.daq = Ni_Daq_Mx_Card(device_name=device_name, logger=logger)

    # Raising edge TTL 
    def shutter_open(self):
        self.daq.set_ao_voltage(self.output_channel, [0,5])

    # Falling edge TTL 
    def shutter_close(self):
        self.daq.set_ao_voltage(self.output_channel, [0,-5])


    class Service(ServiceBase):
        # Raising edge TTL 
        def open(self):
            self._module.open()

        # Falling edge TTL 
        def close(self):
            self._module.close()

    class Client(ClientBase):
        def open(self):
            self._service.open()

        def close(self):
            self._service.close() 
