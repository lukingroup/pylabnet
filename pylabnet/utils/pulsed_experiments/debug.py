import numpy as np
import socket
import time

from pylabnet.utils.logging.logger import LogClient
from pylabnet.utils.helper_methods import load_config
import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.utils.pulseblock.pb_iplot import iplot
from pylabnet.utils.pulseblock.pb_sample import pb_sample
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule
from pylabnet.hardware.staticline import staticline
from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import DIOPulseBlockHandler
from pylabnet.network.client_server import dio_breakout
from pylabnet.network.client_server import si_tt
from pylabnet.scripts.counter.count_histogram import TimeTrace
from pylabnet.network.client_server import count_histogram
from pylabnet.utils.helper_methods import setup_full_service
from pylabnet.utils.pulsed_experiments.pulsed_experiment import PulsedExperiment

from pyvisa import VisaIOError, ResourceManager


from pylabnet.gui.igui.iplot import SingleTraceFig, MultiTraceFig, StaggeredTraceFig


dev_id = 'dev8227'

# Instantiate
logger = LogClient(
    host='140.247.189.82',
    port=18977,
    module_tag=f'ZI HDAWG {dev_id}'
)

# # Instanciate HDAWG driver.
hd = Driver(dev_id, logger=logger)

scaling = 0.1

laser_2 = "sasha"
laser_1 = "toptica"

delta_t_laser_1 = 2e-3 * scaling
delta_t_laser_2 = 2e-3* scaling
wait_lasers = 1e-6

gate_buffer = 0.5e-6
delta_t_gate = 1e-6


# Define the pulse sequence
laser_1_pulse = po.PTrue(ch=laser_1, dur=delta_t_laser_1)
laser_2_pulse = po.PTrue(ch=laser_2, dur=delta_t_laser_2)
gate_pulse = po.PTrue(ch='gate1',  t0=-gate_buffer, dur=delta_t_gate+gate_buffer)

gate_laser_2_pulse = pb.PulseBlock(
 [
    laser_2_pulse,
    gate_pulse,
    ]
)
new_pulse = pb.PulseBlock(laser_1_pulse, name='test')
scan_pulse = pb.PulseBlock(laser_1_pulse, name='scan_block')

scan_pulse.append_pb(
    pb_obj=gate_laser_2_pulse,
    offset = wait_lasers
)

assignment_dict = {
    "sasha": 1,
    "toptica": 2,
    "gate1": 3,
}



sequence_txt = """\

        while (1) {
            $dig_pulse0$  
            wait(1000);
                $dig_pulse1$ 
        }
        """


pe = PulsedExperiment([scan_pulse, new_pulse], assignment_dict, hd=hd, use_template=False, sequence_string=sequence_txt)
pe.prepare_sequence()