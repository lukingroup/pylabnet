
# -*- coding: utf-8 -*-

import numpy as np
from pip import main
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm.simulate import SimulationConfig
from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.utils.decorators.dummy_wrapper import dummy_wrap
import requests
import json

class Driver:
    def __init__(self, device_name='QM', host='192.168.50.97', port=80, logger=None, dummy=False) -> None:
        self.qmm = QuantumMachinesManager(host=host, port='80')
        return

    def execute(self, prog, config):
        qm = self.qmm.open_qm(config)
        job = qm.execute(prog)
        return job

    def simulate(self, prog, config, duration=2000):
        # OPX Simulate
        job = self.qmm.simulate(config, prog, SimulationConfig(duration=duration,
                                                include_analog_waveforms=True,    # include analog waveform names (default True)
                                                include_digital_waveforms=True ))   # include digital waveform  (default True))

        # get DAC and digital samples
        samples = job.get_simulated_samples()
        return job, samples


if __name__== "main":
    from configuration import config
    myQM = Driver()
    
    # prog
    with program() as generate_tt:
        with infinite_loop_():
            play('trigger', 'tt') 
            # play('X', 'e_spin')
            wait(100, 'tt')

    # execute
    myQM.execute()
    pass