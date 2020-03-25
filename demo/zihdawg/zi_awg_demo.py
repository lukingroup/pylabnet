# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWG_Driver
from pylabnet.utils.logging.logger import LogClient

import matplotlib
import numpy as np
import textwrap
import matplotlib.pyplot as plt



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
            wait(getUserReg(0));
            playWave(2, y);
        }
        """)

# Fill in the integer constant AWG_N
sequence = sequence.replace('_c1_', str(AWG_N))


# Create an instance of the AWG Module

awgModule = hd.setup_awg_module(0)

if awgModule is not None:
    hd.compile_upload_sequence(awgModule, sequence)

# Now let's try to output something cool, how about the following Lissajou figure?
a = 3
b = 4
delta = np.pi / 2
num_samples = AWG_N # Should be multiples of 16
t = np.linspace(-np.pi, np.pi, num_samples)


x = np.sin(a * t + delta)
y = np.sin(b * t)
plt.subplot(2, 2, 1)
plt.plot(x, y)

#plt.show()

# Now let's upload it to the HDAWG
hd.dyn_waveform_upload(awgModule, x, 0)
hd.dyn_waveform_upload(awgModule, y, 1)

# TODO: Need triggering



hd.disable_everything()
