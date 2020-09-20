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


# T1 parameteres
delta_t_sasha_t1 = 1e-3
delta_t_start_t1 = 100e-9
t_start_t1 = 0

tau_start = 100e-6
tau_end = 1000e-3
num_tau = 10


# Define the pulse sequence
laser_1_pulse = po.PTrue(ch=laser_1, dur=delta_t_laser_1)
laser_2_pulse = po.PTrue(ch=laser_2, dur=delta_t_laser_2)
gate_pulse = po.PTrue(ch='gate1',  t0=-gate_buffer, dur=delta_t_gate+gate_buffer)


# Gated Optical Pumping Pulse
gate_laser_2_pulse = pb.PulseBlock(
 [
    laser_2_pulse,
    gate_pulse,
    ]
)

scan_pulse = pb.PulseBlock(laser_1_pulse, name='scan_block')

scan_pulse.append_pb(
    pb_obj=gate_laser_2_pulse,
    offset = wait_lasers
)

# T1 pulse
taus = np.linspace(tau_start, tau_end, num_tau)

t1_pb = pb.PulseBlock(
            p_obj_list=[
            po.PTrue(ch='gate1', t0=t_start_t1, dur=delta_t_start_t1),
            ]
        )

for tau in taus:

    t1_pb.append(
        po.PTrue(ch=laser_2, t0=tau, dur=delta_t_sasha_t1)
        )



assignment_dict = load_config('dio_assignment')
awg_number = 0
# Load DIO assignment dict from config files
assignment_dict = load_config('dio_assignment')

# Load placeholder replacement dict from config files
placeholder_dict = load_config('gated_experiment')

pe_scan = PulsedExperiment(
    pulseblocks=scan_pulse, 
    assignment_dict=assignment_dict, 
    hd=hd, 
    template_name="gated_optical_pumping",
    placeholder_dict=placeholder_dict
    )

awg = pe_scan.get_ready(awg_num)