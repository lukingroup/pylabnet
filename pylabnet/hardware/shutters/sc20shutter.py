# -*- coding: utf-8 -*-

from pylabnet.hardware.ni_daqs.nidaqmx_card import Driver
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


""" This file contains the pylabnet Hardware module class for SDC20 Thorlabs shutter.
The shutter is triggered via a TTL signal from a NI DAQmx card
"""


class SC20Shutter:

    def __init__(self, device_name, output_channel, shutter_name='shutter', logger=None):
        """Hardware module class for SDC20 Thorlabs shutter.

        This method connects to NI-DAQmx card and uses the analog output
        to gate SDC20 Thorlabs shutter.

        :device_name: (str) Name of NI DAQ mx card, as displayed in NI MAX
        :ao_channel: (str) Name of output channel where SC20 is connected (e.g. 'ao1', 'ao2')
        :shutter_name: (str, optional) Readable name of shutter (e.g. 'Collection Path')
        """

        # Retrieve member variables
        self.device_name = device_name
        self.output_channel = output_channel
        self.shutter_name = shutter_name
        self.log = logger

        # Instantiate NI DAQ
        self.daq = Driver(
            device_name=device_name,
            logger=logger
        )

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
