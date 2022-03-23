
# -*- coding: utf-8 -*-

import numpy as np
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import infinite_loop_, play, program, wait
from qm.simulate import SimulationConfig
from pylabnet.utils.logging.logger import LogHandler


class Driver:
    def __init__(self, device_name='QM', host='192.168.50.97', port=80, logger=None, dummy=False) -> None:
        # Instantiate log
        self.log = LogHandler(logger=logger)
        self.qmm = QuantumMachinesManager(host=host, port='80')
        self.job = None
        if(self.log is not None):
            self.log.info("quantum machine manager is created!")
        return

    def execute(self, config_QM, prog):
        qm = self.qmm.open_qm(config_QM)
        self.job = qm.execute(prog)
        return self.job

    def simulate(self, config_QM, prog, duration=2000):
        # OPX Simulate
        self.job = self.qmm.simulate(config_QM, prog, SimulationConfig(duration=duration,
                                                                  include_analog_waveforms=True,    # include analog waveform names (default True)
                                                                  include_digital_waveforms=True))   # include digital waveform  (default True))

        # get DAC and digital samples
        samples = self.job.get_simulated_samples()
        return self.job, samples


if __name__ == "__main__":
    from configuration import config
    myQM = Driver()

    # prog
    print('start...')
    with program() as prog:
        with infinite_loop_():
            play('trigger', 'tt')
            # play('X', 'e_spin')
            wait(100, 'tt')

    # execute
    myQM.execute(config, prog)
