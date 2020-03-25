# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import  HDAWG_Driver
from pylabnet.utils.logging.logger import LogClient


dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12345,
    module_tag=f'ZI HDAWG {dev_id}'
)


hd = HDAWG_Driver(dev_id, logger)
hd.enable_output([0, 1, 2, 3, 8])  # Shows error in log server for index 8
hd.disable_output(1)  # Works fine.
hd.disable_everything()
