from pylabnet.utils.logging.logger import LogClient

from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule

from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import DIOPulseBlockHandler

from pylabnet.utils.pulsed_experiments.pulsed_experiment import PulsedExperiment

import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
from pylabnet.utils.pulseblock.pb_iplot import iplot
from pylabnet.utils.pulseblock.pb_sample import pb_sample



# Create Sequence Object and replace placeholder
placeholder_dict = {
    "c1" : AWG_N,
}


# Create Sequence Object and replace placeholder
seq = Sequence(
     hdawg_driver = hd,
     sequence = sequence_txt,
     placeholder_dict=placeholder_dict,
)


pe = PulsedExperiment(pulseblock=None, assignment_dict=None)