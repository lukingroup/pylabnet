from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWGDriver, Sequence, AWGModule
from pylabnet.hardware.staticline.staticline import Staticline

from pylabnet.utils.logging.logger import LogClient


import matplotlib
import numpy as np
import matplotlib.pyplot as plt

dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12346,
    module_tag=f'ZI HDAWG {dev_id}'
)


# Instanciate Hardware class
hd = HDAWGDriver(dev_id, logger)
awg = AWGModule(hd, 0)


staticline_name = 'Laser Green'

# Instantiate Log Client for staticline
logger_staticline = LogClient(
    host='localhost',
    port=12346,
    module_tag=staticline_name
)

# This will throw an error.
sl = Staticline(
    name='DIO-1 HDAWG',
    logger=logger_staticline,
    hardware_module=awg,
    some_param='lol',
    some_int=70
)