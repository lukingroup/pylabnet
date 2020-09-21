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
    port=37542,
    module_tag=f'ZI HDAWG {dev_id}'
)

# # Instanciate HDAWG driver.
hd = Driver(dev_id, logger=logger)

def rabi_element(tau=0, aom_offset=0):
    rabi_element = pb.PulseBlock(
        p_obj_list=[
            po.PTrue(ch='aom', dur=1.1e-6),
            po.PTrue(ch='ctr', t0=0.5e-6, dur=0.5e-6)
        ]
    )
    temp_t = rabi_element.dur

    rabi_element.insert(
        p_obj=po.PTrue(ch='mw_gate', dur=tau, t0=temp_t+0.7e-6)
    )
    temp_t = rabi_element.dur

    rabi_element.insert(
        p_obj=po.PTrue(ch='aom', t0=temp_t+aom_offset, dur=2e-6)
    )
    rabi_element.insert(
        p_obj=po.PTrue(ch='ctr', t0=temp_t, dur=0.5e-6)
    )

    return rabi_element


# Let's choose a microwave duration of 1us.
tau = 1e-6



# Specify the DIO outputs which drive the MW, counter and aom.
assignment_dict = {
    'mw_gate':   15,
    'ctr':      16,
    'aom':      17,
}

# Which awg core to use
awg_num = 1


# Sequence containing two DIO placeholders, and non-DIO palceholders
sequence_txt = """\

        while (1) {
            if (getUserReg($trigger_user_reg$) == $trigger_up_val$) {
                repeat ($repetitions$) {
                $dig_sequence0$  
                wait(1000);
                }
                setUserReg($trigger_user_reg$, $trigger_down_val$);
                $dig_sequence1$
            }
        }
        """

# Replacement values for non-DIO placeholders
placeholder_dict = {
    "trigger_user_reg": 0,
    "repetitions": 0,
    "trigger_up_val" : 0,
    "trigger_down_val" : 1
}

# Pulseblock to replace the DIO placeholder
pulseblocks = [rabi_element(tau), rabi_element(tau+2e-6)]

# Instanciate pulsed experiment
pe_rabi_multi = PulsedExperiment(
    pulseblocks=pulseblocks, 
    assignment_dict=assignment_dict, 
    placeholder_dict=placeholder_dict,
    use_template=False,
    sequence_string=sequence_txt,
    hd=hd, 
    )

# Compile sequence, upload to HDAWG and prepare DIO output
awg = pe_rabi.get_ready(awg_num)