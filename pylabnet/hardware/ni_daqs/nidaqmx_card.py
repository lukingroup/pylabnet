# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware module class for a generic NI DAQ mx card.
"""

import nidaqmx
from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase

import pickle


class Driver:
    """Driver for NI DAQmx card. Currently only implements setting AO voltage"""
    # TODO implement counter

    def __init__(self, device_name, logger=None):
        """Instantiate NI DAQ mx card

        :device_name: (str) Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        """

        # Device name
        self.dev = device_name

        # Log
        self.log = LogHandler(logger=logger)

        # Try to get info of DAQ device to verify connection
        try:
            ni_daq_device = nidaqmx.system.device.Device(name=device_name)
            self.log.info(
                "Successfully connected to NI DAQ '{device_name}' (type: {product_type}) \n"
                "".format(
                    device_name=ni_daq_device.name,
                    product_type=ni_daq_device.product_type
                )
            )

        # If failed, provide info about connected DAQs
        except nidaqmx.DaqError as exc_obj:

            # Log exception message

            # - get names of all connected NI DAQs
            ni_daqs_names = nidaqmx.system._collections.device_collection.\
                DeviceCollection().device_names

            # - exception message
            self.log.exception(
                "NI DAQ card {} not found. \n"
                "There are {} NI DAQs available: \n "
                "    {}"
                "".format(
                    device_name,
                    len(ni_daqs_names),
                    ni_daqs_names
                )
            )

            # Raise exception
            raise exc_obj

    def set_ao_voltage(self, ao_channel, voltages):
        """Set analog output of NI DAQ mx card to a series of voltages

        :ao_channel: (str) Name of output channel (e.g. 'ao1', 'ao2')
        :voltages: (list of int) list of voltages which will be output
        """

        # TODO: Understand the timing between ouput voltages (sample-wise?)
        channel = self._gen_ch_path(ao_channel)

        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(channel)
            task.write(voltages, auto_start=True)

    # Technical methods

    def _gen_ch_path(self, channel):
        """ Auxiliary method to build channel path string.

        :param channel: (str) channel name ['ao1']
        :return: (str) full channel name ['Dev1/ao1']
        """

        return "{device_name}/{channel}".format(
            device_name=self.dev,
            channel=channel
        )


class Service(ServiceBase):

    def exposed_set_ao_voltage(self, ao_channel, voltage_pickle):
        voltages = pickle.loads(voltage_pickle)
        return self._module.set_ao_voltage(
            ao_channel=ao_channel,
            voltages=voltages
        )


class Client(ClientBase):

    def set_ao_voltage(self, ao_channel, voltages):
        voltage_pickle = pickle.dumps(voltages)
        return self._service.exposed_set_ao_voltage(
            ao_channel=ao_channel,
            voltage_pickle=voltage_pickle
        )


class GatedCounter(GatedCtrInterface):
    """ Hardware class for NI gated counter """

    def __init__(self):
        self.ci_channel = None
        self.task = None
        self.duration = 0.1
        self._status = 'Inactive'
        self.current_count = 0

    def activate_interface(self, counter_channel='Dev1/ctr0', physical_channel='/Dev1/20MHzTimebase'):
        """ Activates counter interface (creates a task, does not start it)

        :param counter_channel: (str) channel of counter to use, e.g. 'Dev1/ctr0'
        :param physical_channel: (str) channel of physical counter input, e.g. 'Dev1/PFI0'
        """

        # Create a task - note we have to be careful and close the task if something goes wrong
        self.task = nidaqmx.Task()

        try:
            self.ci_channel = self.task.ci_channels.add_ci_count_edges_chan(counter_channel)
            self.ci_channel.ci_count_edges_term = physical_channel
            self._status = 'Active, but not counting'

        except nidaqmx.DaqError:
            self.task.close()
            self._status = 'Inactive'
            print('Failed to activate counter')
            raise

    def init_ctr(self, bin_number=0.1, gate_type=None):
        """ Initializes gated counter parameters

        :param bin_number: (double) number of seconds to read for
        :param gate_type: (not used)
        """
        self.duration = bin_number
        pass

    def close_ctr(self):
        """ Stops the task and closes it.

        The interface must be reactivated using activate_interface command in order to resume counting """

        try:
            self.task.stop()
        except nidaqmx.DaqError:
            pass
        self._status = 'Inactive'
        self.task.close()

    def start_counting(self):
        """ Starts the counter """

        self._status = 'Counting'
        try:
            self.task.start()
            self.current_count = self.task.read()
        except nidaqmx.DaqError:
            pass

    def terminate_counting(self):
        pass

    def get_status(self):
        """ Returns status of the counter

        :return: (str) whether or not the counter is active, and counting
        """

        return self._status

    def get_count_ar(self, timeout=-1):
        pass
