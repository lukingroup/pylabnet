import numpy as np

import matplotlib.pyplot as plt

import pyvisa
from pylabnet.utils.logging.logger import LogClient
import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb

from pylabnet.utils.pulseblock.pb_check import PbChecker



from pyvisa import VisaIOError, ResourceManager

from pylabnet.hardware.oscilloscopes.tektronix_tds2004C import Driver
from pylabnet.network.client_server.tektronix_tds2004C import Client




######################HDAWG PART###################################
# # Connect to HDAWG
# dev_id = 'dev8040'

# Instantiate logger.
logger = LogClient(
    host='192.168.1.2',
    port=2000,
    module_tag='Pulsechecker'
)

# # Instanciate HDAWG driver.
# hd = Driver(dev_id, logger=logger)


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

    rabi_element.dflt_dict = dict(
        aom=po.DFalse(),
        ctr=po.DFalse(),
        mw_gate=po.DFalse()
    )

    return rabi_element


# Let's choose a microwave duration of 1us.
tau = 1e-6
rabi_pulse = rabi_element(tau)

# # Specify the DIO outputs which drive the MW, counter and aom.
# assignment_dict = {
#     'mw_gate':   15,
#     'ctr':      17,
#     'aom':      31,
# }

# # Instanciate pulseblock handler.
# pb_handler = DIOPulseBlockHandler(
#     pb = rabi_pulse,
#     assignment_dict=assignment_dict,
#     hd=hd
# )

# # Generate .seqc instruction set which represents pulse sequence.
# dig_pulse_sequence = pb_handler.get_dio_sequence()

# # SeLect HD channel grouping.
# hd.set_channel_grouping(0)

# # Enable output 0 used for triggering.
# hd.enable_output(0)

# # This sequence will send out a trigger and execute the commands  dig_pulse (yet to be specified).
# sequence_txt = """\

#         while (1) {

#           // Trigger to scope.
#           setTrigger(1);

#           _dig_pulse_

#           setTrigger(0);

#           // Wait
#           wait(1000);

#         }
#         """

# # Create Sequence instance.
# seq = Sequence(hd, sequence_txt, ['dig_pulse'])

# # Replace dig_pulse placeholder by digital pulse sequence instruction set.
# seq.replace_placeholder('dig_pulse', dig_pulse_sequence)

# # Create an instance of the AWG Module.
# awg = AWGModule(hd, 0)
# awg.set_sampling_rate('2.4 GHz') # Set 2.4 GHz sampling rate.

# # Upload sequence.
# if awg is not None:
#     awg.compile_upload_sequence(seq)

# # Now we're almost ready, we only have to make sure that the 8 bit buses for bits 15, 17, and 31 are driven.
# # This can be done automatically by calling the following:

# pb_handler.setup_hd()

# # Start the AWG
# awg.start()

######################SCOPE PART###################################

# Connect to scope
scope = Client(
    host='192.168.0.17',
    port=2253
)

# Set trigger source to CH4.
scope.set_trigger_source('CH4')

# Let's set the timebase accordingly
timespan = 1e-6 # 1us per div --> total window of 10us
scope.set_timing_scale(timespan)

# Let's set the scales accordingly (we expect signal from 0 to 3.3V)
for channel in ['CH1', 'CH2', 'CH3', 'CH4']:

    # Set scale to 1V/div, with 10 divs this gives us a range of 10V.
    scope.set_channel_scale(channel, 1)

    # Set the zero horizontal position to 0V.
    scope.set_channel_pos(channel, 0)

# Let's set the trigger level to 50%.
scope.trig_level_to_fifty()

# Set timebase to 500ns / div.
scope.set_timing_scale(500e-9 )

# Let's move the trace 2.5 us to the right.
scope.set_horizontal_position(+2.5e-6)

#scope.plot_traces(['CH1', 'CH2', 'CH3'])


# Read out traces

mw_gate_data = scope.read_out_trace('CH1', curve_res=2)
ctr_data = scope.read_out_trace('CH2', curve_res=2)
aom_data = scope.read_out_trace('CH3', curve_res=2)

# Construct data dict
data_dict = {
    'mw_gate':  [mw_gate_data['ts'], mw_gate_data['trace']],
    'ctr':      [ctr_data['ts'], ctr_data['trace']],
    #'aom':      [aom_data['ts'], aom_data['trace']]
}

# Define tolerances

# Allow for one sample timing tolerance in each direction
x_tol = 1*3.33e-9  # in s
y_tol = 0.1  # in V

sampling_rate = 300e-6

pb_check = PbChecker(
    pb=rabi_pulse,
    sampling_rate=sampling_rate,
    data_dict=data_dict,
    x_tol=x_tol,
    y_tol=y_tol,
    logger=logger
)
