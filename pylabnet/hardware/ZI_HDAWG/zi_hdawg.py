# -*- coding: utf-8 -*-

"""
This file contains the pylabnet Hardware class for the Zurich Instruments HDAWG.
"""

import zhinst.utils
import re

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class HDAWG_Driver():

    def disable_everything(self):
        """ Create a base configuration: Disable all available outputs, awgs, demods, scopes,.. """
        zhinst.utils.disable_everything(self.daq, self.device_id)

    def __init__(self, device_id, logger=None, api_level=6):
        """ Instantiate AWG

        :logger: instance of LogClient class
        :device_id: Device id of connceted ZI HDAWG, for example 'dev8060'
        :api_level: API level of zhins API
        """

        # Part of this code has been modified from ZI's Zurich Instruments LabOne Python API Example

        err_msg = "This example can only be ran on an HDAWG."
        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate with devices via the data server.
        # - the device ID string that specifies the device branch in the server's node hierarchy.
        # - the device's discovery properties.
        (daq, device, props) = zhinst.utils.create_api_session(device_id, api_level, required_devtype='HDAWG',
                                                        required_err_msg=err_msg)
        zhinst.utils.api_server_version_check(daq)

        self.daq = daq
        self.device_id = device

        # Create a base configuration: Disable all available outputs, awgs, demods, scopes,...
        self.disable_everything()

        # read out number of channels from property dictionary
        self.num_outputs = int(re.compile('HDAWG(4|8{1})').match(props['devicetype']).group(1))

    def seti(self, node, new_int):
        """
        Warapper for daq.setInt commands. For instance, instead of
        daq.setInt('/dev8040/sigouts/0/on', 1), write

        hdawg.seti('sigouts/0/on, 1)

        :node: Node which will be appended to '/device_id/'
        :new_int: New value for integer
        """

        self.daq.setInt('/{device_id}/{node}'.format(device_id=self.device_id, node=node), new_int)

    def check_output_index(self, output_index):
        """ Checks if output index exists"""
        assert output_index in range(self.num_outputs), "This device has only {} channels, channel index {} is invalid.".format(self.num_outputs, output_index)
        return output_index

    def enable_output(self, output_index):
        """
        Enables wave output.

        Channel designation uses channel index (0 to 7),
        not channel number (1 to 8).

        :output_index: Indicating wave output 0 to 7
        """

        self.seti('sigouts/{output_index}/on'.format(output_index=self.check_output_index(output_index)), 1)

    def disable_output(self, output_index):
        """
        Disables wave output.

        :output_index: Indicating wave output 0 to 7
        """

        self.seti('sigouts/{output_index}/on'.format(output_index=self.check_output_index(output_index)), 0)