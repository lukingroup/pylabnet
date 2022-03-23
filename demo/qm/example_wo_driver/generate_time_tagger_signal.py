from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm.simulate import SimulationConfig
from configuration import config
import time

qmm = QuantumMachinesManager(host='192.168.50.97', port='80')

with program() as generate_tt:
    with infinite_loop_():
        # play('trigger_tt_pulse', 'tt') 
        play('X', 'e_spin')
        wait(500, 'tt')


qm = qmm.open_qm(config)
job = qm.execute(generate_tt)

