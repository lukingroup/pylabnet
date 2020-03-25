# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWG_Driver
from pylabnet.utils.logging.logger import LogClient


dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12345,
    module_tag=f'ZI HDAWG {dev_id}'
)

# Instanciate Hardware class
hd = HDAWG_Driver(dev_id, logger)

# Select channel grouping
hd.set_channel_grouping(0)


outputs = [0, 1]
hd.enable_output(outputs)

for output in outputs:
    hd.set_output_range(output, 0.2)

hd.disable_everything()
