# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware module class for a generic NI DAQ mx card.

"""

import nidaqmx  
from pylabnet.utils.logging.logger import LogHandler


class Ni_Daq_Mx_Card():

    def __init__(self, device_name, logger=None):
        """Instantiate NI DAQ mx card

        :device_name: Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        """

        # Device name
        self.dev = device_name

        # Log
        self.log = LogHandler(logger=logger)

        # Try to get infos of DAQ device to verify connection
        try:
            ni_daq_device = nidaqmx.system.device.Device(name = device_name)
            self.log.info(
                "Successfully connected to NI DAQ '{device_name}' (type: {product_type}) \n".format\
                    (device_name = ni_daq_device.name, product_type=ni_daq_device.product_type)
                )
        
        # If failed, provide info about connected DAQs
        except:
            # Get names of all connected NI DAQs
            ni_daqs_names = nidaqmx.system._collections.device_collection.DeviceCollection().device_names
            self.log.error('NI DAQ {device_name} not found: \n'.format(device_name=device_name))
            self.log.error('Available {} NI DAQs: \n'.format(len(ni_daqs_names)))
            self.log.error('{}  \n'.format(ni_daqs_names))

    def get_channel_path(self, channel):
        return("{device_name}/{channel}".format(device_name = self.dev, channel=channel))

    def set_ao_voltage(self, ao_channel, voltages):
        """Set analog output of NI DAQ mx card to series of voltages

        :ao_channel: Name of output channel (e.g. 'ao1', 'ao2')
        :voltages: list of volateges which will be output 
        TODO: Understand the timing between ouput voltages (sample-wise?)
        """
        channel = self.get_channel_path(ao_channel)

        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(channel)
            task.write(voltages, auto_start=True)



