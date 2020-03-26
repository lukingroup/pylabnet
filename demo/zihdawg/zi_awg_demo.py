# -*- coding: utf-8 -*-

"""
This module demonstrates the use of the ZI HDAWG Hardware Class.
"""


from pylabnet.hardware.zi_hdawg.zi_hdawg import HDAWG_Driver, Sequence, AWGModule
from pylabnet.utils.logging.logger import LogClient

import matplotlib
import numpy as np
import textwrap
import matplotlib.pyplot as plt


# Now let's try to output something cool, how about the following Lissajou figure?
a =3
b = 4
delta = np.pi/2
num_samples = 16*100 # Should be multiples of 16
t = np.linspace(-np.pi, np.pi, num_samples)


x = np.sin(a * t + delta)
y = np.sin(b * t)
plt.subplot(2, 2, 1)
plt.plot(x, y)



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

AWG_N = 1600
sequence_txt = """\
        const AWG_N = _c1_;

        wave x = zeros(AWG_N);
        wave y = ones(AWG_N);

        while(1){
            setTrigger(1);
            setTrigger(0);
            playWave(1, x);
            playWave(2, y);
        }
        """

# Create Sequence Object and replace placeholder
seq = Sequence(hd, sequence_txt, ['c1'])
seq.replace_placeholder('c1', AWG_N)

# Create an instance of the AWG Module
awg = AWGModule(hd, 0)
awg.set_sampling_rate(0) # Set 2.4 GHz sampling rate


# Upload sequence
if awg is not None:
    awg.compile_upload_sequence(seq)

    # Now let's upload it to the HDAWG
awg.dyn_waveform_upload(x, 0)
awg.dyn_waveform_upload(y, 1)