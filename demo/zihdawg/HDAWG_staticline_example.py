from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWGDriver, Sequence, AWGModule
from pylabnet.hardware.staticline.staticline import Staticline

from pylabnet.utils.logging.logger import LogClient


import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import time

dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12346,
    module_tag=f'ZI HDAWG {dev_id}'
)


# Instanciate Hardware class
hd = HDAWGDriver(dev_id, logger)


staticline_name = 'HDAWG DIO'

# Instantiate Log Client for staticline
logger_staticline = LogClient(
    host='localhost',
    port=12346,
    module_tag=staticline_name
)


all_DIOs =  [Staticline(
    name=f'DIO-{i} HDAWG',
    logger=logger_staticline,
    hardware_module=hd,
    DIO_bit=i,
) for i in range(32)]

for dio_staticline in all_DIOs:
    dio_staticline.up()
    time.sleep(0.3)

for dio_staticline in all_DIOs[::-1]:
    dio_staticline.down()
    time.sleep(0.3)
    dio_staticline.up()
    time.sleep(0.3)


hd.disable_everything()
hd.reset_DIO_outputs()