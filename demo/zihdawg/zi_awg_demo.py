# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import  HDAWG_Driver
from pylabnet.utils.logging.logger import LogClient




# Instantiate logger
logger = LogClient(
    host='localhost',
    port=12345,
    module_tag='ZI HDAWG'
)

dev_id = 'dev8040'
hd = HDAWG_Driver(dev_id, logger)
hd.enable_output(1)
hd.enable_output(7)
hd.disable_everything()