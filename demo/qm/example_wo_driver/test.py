# note that the programe does not import again once it was imported, which means config will not be updated until one restarts the kernel 
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm.simulate import SimulationConfig
from configuration import config
import time
import numpy as np
import matplotlib.pyplot as plt


# generate tt and measure it

readout_len =2000
signal_th = config['elements']['snspd']['outputPulseParameters']['signalThreshold']
config['pulses']['tt_window']['length'] = readout_len

qmm = QuantumMachinesManager(host='192.168.50.97', port='80')

with program() as generate_tt_and_cal:\

    times = declare(int, size=10000)
    idx = declare(int)
    times_st = declare_stream()
    counts = declare(int)
    counts_st = declare_stream()
    adc_st = declare_stream(adc_trace=True)

    it = declare(int)

    measure("tt_window", "snspd", adc_st, time_tagging.analog(times, readout_len, counts))
    wait(100, 'tt')
    play('trigger', 'tt') 
    save(counts, counts_st)

    with for_(idx, 0, idx < counts, idx+1):
        save(times[idx], times_st)

    with stream_processing():
        adc_st.input1().save_all('adc')
        times_st.save_all('times')
        counts_st.save_all('counts')


# creating communication with the OPX
qmm = QuantumMachinesManager(host='192.168.50.97', port='80')

# open a quantum machine
qm = qmm.open_qm(config)

# execute QUA program on the QM
job = qm.execute(generate_tt_and_cal)



# results handing
handles = job.result_handles
adc_handle = handles.get('adc')
times_handle = handles.get('times')
counts_handle = job.result_handles.get('counts')
handles.wait_for_all_values()
adc = adc_handle.fetch_all()['value'][0]
diff = np.concatenate((np.array([0, 1]), np.diff(adc)))
times = times_handle.fetch_all()['value']
counts = counts_handle.fetch_all()['value']


# plotting and analysing
fig, ax1 = plt.subplots()
ax1.plot(adc, 'r-')
ax1.set_ylabel('raw adc', color='r')
ax1.hlines(signal_th, 0, readout_len)
plt.title('{} counts'.format(counts), size=12)
plt.show()

print()