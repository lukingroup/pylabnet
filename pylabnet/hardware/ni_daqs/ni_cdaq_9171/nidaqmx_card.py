# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware module class for a generic NI DAQ mx card.

"""

import nidaqmx

class ni_daq_mx_card():

    def __init__(self, device_name):
        """Instantiate NI DAQ mx card

        :device_name: Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        """

        # Device name
        self.dev = device_name

    def getpath(self, channel):
        return("{device_name}/{channel}".format(device_name = self.dev, channel=channel))


    def set_ao_voltage(self, ao_channel, voltages):
        """Instantiate NI DAQ mx card

        :ao_channel: Name of output channel (e.g. 'ao1', 'ao2')
        :voltages: list of volates which will be output sample by sample
        """
        channel = self.getpath(ao_channel)

        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(channel)
            task.write(voltages, auto_start=True)



#Testing the class
device_name = 'cDAQ1Mod1'

daq = ni_daq_mx_card(device_name=device_name)

ao_channel = 'ao2'
voltages = [0,5,3,1,0]


for i in range(1000):
    daq.set_ao_voltage(ao_channel, voltages)