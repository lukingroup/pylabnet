import sys
sys.path.append("C:\\Users\\Control Software\\pylabnet\\pylabnet\\hardware\\superK")
import NKTP_DLL as NKTP_DLL
# -*- coding: utf-8 -*-

"""
Description: WILL ADD LATER...
"""

import time
import numpy as np

from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.decorators.dummy_wrapper import dummy_wrap

class Driver:
    def __init__(self, com_port='COM12', devID=15, logger=None):
        # port and devID
        self.com_port = com_port
        self.devID = devID

        # Log
        self.log = LogHandler(logger=logger)
        self.log.info('launching superK driver')
        return

    
    def emission_on(self):
        # emission on
        result = NKTP_DLL.registerWriteU8(self.com_port, self.devID , 0x30, 0x03, -1)
        self.log.info('Setting emission ON - Extreme:'+ str( NKTP_DLL.RegisterResultTypes(result)) )
        return result

    def emission_off(self):
        # emission on
        result = NKTP_DLL.registerWriteU8(self.com_port, self.devID , 0x30, 0x00, -1)
        self.log.info('Setting emission OFF - Extreme:'+  str( NKTP_DLL.RegisterResultTypes(result)) )
        return result

    def read_power(self):
        """return the power level setpont, should be a value between 0~0.6 """
        rdResult, readValue = NKTP_DLL.registerReadU16(self.com_port, self.devID, 0x37, -1)
        self.log.info('readValue:' + str(readValue) + '; read result message: ' + str(NKTP_DLL.RegisterResultTypes(rdResult)) )
        return float(readValue) / 1000.0
    
    def set_power(self, setpoint):
        """setpoint: the power level setpont, should be a value between 0~0.6 """
        pow_permille = int(setpoint * 1000)
        rdResult = NKTP_DLL.registerWriteU16(self.com_port, self.devID, 0x37, pow_permille, -1)
        self.log.info( 'read result message: ' + str(NKTP_DLL.RegisterResultTypes(rdResult)) )
        return rdResult

