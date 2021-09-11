# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware module class for a generic NI DAQ mx card.
"""

import nidaqmx
import time
import numpy as np

from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.decorators.dummy_wrapper import dummy_wrap


class Driver:
    """Driver for NI DAQmx card. Currently only implements setting AO voltage"""
    # TODO implement counter

    def __init__(self, device_name, logger=None, dummy=False):
        """Instantiate NI DAQ mx card

        :device_name: (str) Name of NI DAQ mx card, as displayed in the measurement and automation explorer
        """

        # Device name
        self.dev = device_name

        # Log
        self.log = LogHandler(logger=logger)
        self.dummy = dummy

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
        except (nidaqmx.DaqError, OSError):

            # Log exception message

            # - get names of all connected NI DAQs
            try:
                ni_daqs_names = nidaqmx.system._collections.device_collection.\
                    DeviceCollection().device_names

                # - exception message
                self.log.error(
                    "NI DAQ card {} not found. \n"
                    "There are {} NI DAQs available: \n "
                    "    {}"
                    "".format(
                        device_name,
                        len(ni_daqs_names),
                        ni_daqs_names
                    )
                )
            except:
                self.log.error('No NI modules found')
            if self.dummy:
                self.log.info('Entering dummy mode instead')

        self.counters = {}

    @dummy_wrap
    def set_ao_voltage(self, ao_channel, voltages):
        """Set analog output of NI DAQ mx card to a series of voltages

        :ao_channel: (str) Name of output channel (e.g. 'ao1', 'ao2')
        :voltages: (list of int) list of voltages which will be output
        """

        # TODO: Understand the timing between output voltages (sample-wise?)
        channel = self._gen_ch_path(ao_channel)

        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(channel)
            task.write(voltages, auto_start=True)

    def get_ai_voltage(self, ai_channel, num_samples=1, max_range=10.0):
        """Measures the analog input voltage of NI DAQ mx card

        :param ao_channel: (str) Name of output channel (e.g. 'ao1', 'ao2')
        :aram num_samplies: (int) Number of samples to take
        :param max_range: (float) Maximum range of voltage that will be measured
        """
        channel = self._gen_ch_path(ai_channel)
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(channel)
            task.ai_channels[0].ai_rng_high = max_range
            return task.read(number_of_samples_per_channel=num_samples)
        return -1

    def get_di_state(self, port, di_channel):
        """Measures the state of a digital Input of a of NI DAQ mx card

        :param port: (str) port name ['port0']
        :param channel: (str) channel name ['line1']
        """
        channel = self._gen_di_ch_path(port, di_channel)
        with nidaqmx.Task() as task:
            task.di_channels.add_di_chan(channel, line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
            return task.read(number_of_samples_per_channel=1)
        return -1

    def create_timed_counter(
        self, counter_channel, physical_channel, duration=0.1, name=None
    ):
        """ Creates a software timed counter channel

        :param counter_channel: (str) channel of counter to use
            e.g. 'Dev1/ctr0'
        :param physical_channel: (str) physical channel of counter
            e.g. 'Dev1/PFI0'
        :param duration: (float) number of seconds for software-timed
            counting inverval
        :param name: (str) Name to use as a reference for counter in
            future calls

        :return: (str) name of the counter to use in future calls
        """

        # Create a default name if necessary
        if name is None:
            name = f'counter_{len(self.counters)}'

        # Create counter task and assign parameters
        self.counters[name] = TimedCounter(
            logger=self.log,
            counter_channel=self._gen_ch_path(counter_channel),
            physical_channel='/' + self._gen_ch_path(physical_channel)
        )
        self.counters[name].set_parameters(duration)

        return name

    def start_timed_counter(self, name):
        """ Starts a timed counter

        :param name: (str) name of counter to start
            Should be return value of create_timed_counter()
        """

        self.counters[name].start()

    def stop_timed_counter(self, name):
        """ Stops a timed counter

        :param name: (str) name of counter to stop
            Should be return value of create_timed_counter()
        """

        self.counters[name].terminate_counting()

    def close_timed_counter(self, name):
        """ Closes a timed counter

        :param name: (str) name of counter to close
        """

        self.counters[name].close()

    def get_count(self, name):
        """ Returns the count

        :param name: (str) name of the counter to use
        :return: (int) value of the count
        """

        return int(self.counters[name].count)

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

    def _gen_di_ch_path(self, port, di_channel):
        """ Auxiliary method to build channel path string for digital inputs.

        :param port: (str) port name ['port0']
        :param channel: (str) channel name ['line0:1']
        :return: (str) full channel name ['Dev1/port0/line0:1']
        """

        return f"{self.dev}/{port}/{di_channel}"


class TimedCounter:
    """ Hardware class for NI gated counter """

    def __init__(self, logger=None, counter_channel='Dev1/ctr0', physical_channel='/Dev1/20MHzTimebase'):
        """ Activates counter interface (creates a task, does not start it)

        :param logger: instance of LogHandler
        :param counter_channel: (str) channel of counter to use, e.g. 'Dev1/ctr0'
        :param physical_channel: (str) channel of physical counter input, e.g. 'Dev1/PFI0'
        """

        self.log = logger
        self.ci_channel = None
        self.task = None
        self.duration = 0.1
        self._status = 'Inactive'
        self.count = 0

        # Create a task - note we have to be careful and close the task if something goes wrong
        self.task = None
        self.activate_task(counter_channel, physical_channel=physical_channel)

    def activate_task(self, counter_channel='Dev1/ctr0', physical_channel='/Dev1/20MHzTimebase'):
        """ Activates task. Must be used to restart counting if the close command is called """

        # Create a task - note we have to be careful and close the task if something goes wrong
        self.task = nidaqmx.Task()

        try:
            self.ci_channel = self.task.ci_channels.add_ci_count_edges_chan(counter_channel)
            self.ci_channel.ci_count_edges_term = physical_channel
            self._status = 'Active, but not counting'
            self.log.info(f'Created counter {counter_channel} on '
                          f'physical channel {physical_channel}')

        except nidaqmx.DaqError:
            self.task.close()
            self._status = 'Inactive'
            msg_str = f'Failed to activate counter {counter_channel} with physical channel {physical_channel}'
            self.log.error(msg_str)

    def set_parameters(self, duration=0.1):
        """ Initializes gated counter parameters

        :param duration: (float) number of seconds to read for
        """

        self.duration = duration

    def close(self):
        """ Stops the task and closes it.

        The interface must be reactivated using activate_interface command in order to resume counting """

        try:
            self.task.stop()
        except nidaqmx.DaqError:
            self.log.warn(f'Failed to stop NI DAQmx task {self.task.name}')
        self._status = 'Inactive'
        self.task.close()

    def start(self):
        """ Starts the counter """

        self._status = 'Counting'
        try:
            current_time = time.time()
            self.task.start()
            while time.time() - current_time < self.duration:
                pass
            self.task.stop()
            self.count = self.task.read()
        except nidaqmx.DaqError:
            self.log.warn(f'Failed to count on {self.task.name}')

    def terminate_counting(self):
        """ Terminates the counter """

        try:
            self.task.stop()
        except nidaqmx.DaqError:
            self.log.warn(f'Failed to stop {self.task.name}')

        self._status = 'Active, but not counting'

    def get_status(self):
        """ Returns status of the counter

        :return: (str) whether or not the counter is active, and counting
        """

        return self._status


if __name__ == '__main__':
    port = 'port1'
    channel = 'line5'
    dev = Driver('Dev1')
    dev.get_di_state(port=port, di_channel=channel)
