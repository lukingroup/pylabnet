import numpy as np

import matplotlib.pyplot as plt

import pyvisa
from pylabnet.utils.logging.logger import LogClient
from pyvisa import VisaIOError, ResourceManager

from pylabnet.hardware.oscilloscopes.tektronix_tds2004C import Driver
from pylabnet.network.client_server.tektronix_tds2004C import Client


scope = Client(
    host='192.168.0.17',
    port=2253
)