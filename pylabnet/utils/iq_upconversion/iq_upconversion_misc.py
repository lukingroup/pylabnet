import numpy as np


def get_power_at_harmonics(sa, lo_freq, if_freq, harmonics):
    #print("test")
    trace = sa.read_trace()
    powers = np.zeros(len(harmonics))
    for i in range(len(harmonics)):
        freq = lo_freq + if_freq * harmonics[i]
        powers[i] = np.interp(freq, trace[:, 0], trace[:, 1])
    return powers
