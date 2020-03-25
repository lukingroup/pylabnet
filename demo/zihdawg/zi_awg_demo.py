# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWG_Driver
from pylabnet.utils.logging.logger import LogClient
import textwrap



dev_id = 'dev8040'

# Instantiate
logger = LogClient(
    host='localhost',
    port=12345,
    module_tag=f'ZI HDAWG {dev_id}'
)

# Instanciate Hardware class
hd = HDAWG_Driver(dev_id, logger)

# Select channel grouping
hd.set_channel_grouping(0)


outputs = [0, 1]

# Enable the outputs and set corresponding ranges
hd.enable_output(outputs)
for output in outputs:
    hd.set_output_range(output, 0.2)


AWG_N = 16000
sequence = textwrap.dedent("""\
        const AWG_N = _c1_;
        wave x = zeros(AWG_N);
        wave y = zeros(AWG_N);

        while(1){
            setTrigger(1);
            setTrigger(0);
            playWave(1, x);
            playWave(2, y);
        }
        """)

# Fill in the integer constant AWG_N
sequence = sequence.replace('_c1_', str(AWG_N))


hd.set_channel_grouping(1)

# Create an instance of the AWG Module

awgModule = hd.setup_awg_module(1)

if awgModule is not None:
    hd.compile_upload_sequence(awgModule, sequence)


hd.disable_everything()
