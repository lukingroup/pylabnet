# -*- coding: utf-8 -*-

from pylabnet.hardware.ni_daqs.nidaqmx_card import NiDaqMxCard
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


"""
This file contains the pylabnet Hardware module class for SDC20 Thorlabs shutter.
The shutter is triggered via a TTL signal from a NI DAQmx card
"""

class SC20Shutter():

    def __init__(self, device_name, output_channel, shutter_name, logger=None):
        """Instantiate Harware class for SC20 Thorlabs by instanciating NI DAQ card and assiging channel
        :device_name: (string) Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        :ao_channel: (string)  Name of output channel where SC20 is connected(e.g. 'ao1', 'ao2')
        :shutter_name: (string) Readable name of shutter (e.g. 'Collection Path')
        """

        # Retrieve member variables
        self.device_name = device_name
        self.output_channel = output_channel
        self.shutter_name = shutter_name
        self.log = logger

        # Instanciate NI DAQ
        self.daq = NiDaqMxCard(device_name=device_name, logger=logger)

        # Set AO to 0V
        self.daq.set_ao_voltage(self.output_channel, [0])

        # Keep track of state
        self.is_open = False

    # Raising edge opens shutter
    def open(self):
        self.daq.set_ao_voltage(self.output_channel, [5])
        self.is_open = True
        self.log.info('Opened shutter {}  \n'.format(self.shutter_name))

    # Falling edge closes shutter
    def close(self):
        self.daq.set_ao_voltage(self.output_channel, [0])
        self.is_open = False
        self.log.info('Closed shutter {}  \n'.format(self.shutter_name))

    def get_is_open(self):
        return self.is_open

    def get_name(self):
        return self.shutter_name

    class Service(ServiceBase):

        def exposed_open(self):
            return self._module.open()

        def exposed_close(self):
            return self._module.close()

        def exposed_get_name(self):
            return self._module.get_name()

        def exposed_get_is_open(self):
            return self._module.get_is_open()

    class Client(ClientBase):
        def open(self):
            return self._service.exposed_open()

        def close(self):
            return self._service.exposed_close()

        def get_name(self):
            return self._service.exposed_get_name()

        def get_is_open(self):
            return self._service.exposed_get_is_open()
