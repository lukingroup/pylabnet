from pylabnet.utils.logging.logger import LogClient, LogHandler

import matplotlib
import numpy as np
import matplotlib.pyplot as plt

dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12348,
    module_tag=f'ZI HDAWG {dev_id}'
)

#log = LogHandler(logger=logger)
#log.info('lol')

