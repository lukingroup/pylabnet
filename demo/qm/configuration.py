from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm.simulate import SimulationConfig
import numpy as np
from scipy.signal import gaussian

def IQ_imbalance(g, phi):
    c = np.cos(phi)
    s = np.sin(phi)
    n = 1 / ((1 - g ** 2) * (2 * c ** 2 - 1))
    return [float(n * x) for x in [(1 - g) * c, (1 + g) * s, (1 - g) * s, (1 + g) * c]]

##############
# parameters #
##############

# Frequencies in units of Hz
e_spin_if_freq = 100e6
e_spin_lo_freq = 1e9
n_spin_if_freq = 80e6
eom_freq = 300e6

# Waveforms: lengths in ns; amplitudes in voltage.
gauss_len = 60; gauss_wf = (0.30 * gaussian(gauss_len, gauss_len//5)).tolist()
e_spin_const_len = 16; e_spin_const_amp = 0.4
e_spin_X_len = 500; e_spin_X_wf = (0.30 * gaussian(e_spin_X_len, e_spin_X_len//5)).tolist()
e_spin_Y_len = 500; e_spin_Y_wf = (0.30 * gaussian(e_spin_Y_len, e_spin_Y_len//5)).tolist()
e_spin_x_len = 60; e_spin_x_wf = (0.15 * gaussian(e_spin_x_len, e_spin_x_len//5)).tolist()
n_spin_const_len = 500; n_spin_const_amp = 0.4
tt_len = 400; t_ary_tt = np.arange(tt_len); tt_wf =(0.45 * np.exp( -( (t_ary_tt - tt_len//2)/ (tt_len//5.) )**6 )).tolist()
reset_len = 300
trigger_tt_len = 20
res_read_len = 200

config = {

    'version': 1,

    'controllers': {

        'con1': {
            'type': 'opx1',
            'analog_outputs': {
                1: {'offset': 0.0},  # electronic spin I
                2: {'offset': 0.0},  # electronic spin Q
                3: {'offset': 0.0},  # nucleus spin
                4: {'offset': 0.0},  # phase read laser EOM
                5: {'offset': 0.0},  # 
                6: {'offset': 0.0},  # 
            },
            'digital_outputs': {
                1: {},  # electronic spin switch 1
                2: {},  # electronic spin switch 2
                3: {},  # reset laser AOM
                4: {},  # resonant read laser AOM
                5: {},  # phase read laser AOM
                6: {},  # trigger tt
            },
            'analog_inputs': {
                1: {'offset': 0, 'gain_db': -10},  # snspd
            }
        }
    },

    'elements': {

        'e_spin': {
            'mixInputs': {
                'I': ('con1', 1),
                'Q': ('con1', 2),
                'lo_frequency': e_spin_lo_freq,
                'mixer': 'mixer_e_spin'
            },
            'intermediate_frequency': e_spin_if_freq,
            'digitalInputs': {
                'switch1': {'port': ('con1', 1), 'delay': 136, 'buffer': 0},
                'switch2': {'port': ('con1', 2), 'delay': 140, 'buffer': 0}
            },
            'operations': {
                'const': 'e_spin_const_pulse',
                'const_y': 'e_spin_const_y_pulse',
                'gauss': 'gauss_iq_pulse',
                'X': 'X_pulse',
                'Y': 'Y_pulse',
                'x': 'x_pulse',
            }
        },

        'n_spin': {
            'singleInput': {'port': ('con1', 3)},
            'intermediate_frequency': n_spin_if_freq,
            'digitalInputs': {'switch2': {'port': ('con1', 2), 'delay': 0, 'buffer': 0}},
            'operations': {
                'const': 'n_spin_const_pulse'
            }
        },

        'reset_laser': {
            'digitalInputs': {
                'AOM': {'port': ('con1', 3), 'delay': 0, 'buffer': 0},
            },
            'operations': {
                'reset': 'reset_pulse',
            }
        },

        'resonant_read_laser': {
            'digitalInputs': {
                'AOM': {'port': ('con1', 4), 'delay': 0, 'buffer': 0},
            },
            'operations': {
                'readout': 'res_readout_pulse'
            }
        },

        'phase_read_laser': {
            'singleInput': {'port': ('con1', 4)},
            'intermediate_frequency': eom_freq,
            'digitalInputs': {
                'AOM': {'port': ('con1', 5), 'delay': 0, 'buffer': 0},
            },
            'operations': {
            }
        },

        'tt': {
            'singleInput': {'port': ('con1', 6)},
            'digitalInputs': {
                'AOM': {'port': ('con1', 6), 'delay': 0, 'buffer': 0},
            },
            'operations': {
                'trigger': 'trigger_tt_pulse'
            }
        },

        'snspd': {

            # blanked input
            'singleInput': {'port': ('con1', 2)},

            'operations': {
                'tt_window': 'tt_window',
            },
            'outputs': {
                'out1': ('con1', 1)
            },
            'time_of_flight': 28,
            'smearing': 0,
            'outputPulseParameters': {
                'signalThreshold': 100,
                'signalPolarity': 'RISING',
                'derivativeThreshold': 0,
                'derivativePolarity': 'ABOVE'
            }
        },
    },

    "pulses": {

        'e_spin_const_pulse': {
            'operation': 'control',
            'length': e_spin_const_len,
            'waveforms': {
                "I": "e_spin_const_wf",
                # "I": "zero_wf",
                "Q": "zero_wf",
                # "Q": "e_spin_const_wf"
            },
            'digital_marker': 'ON'
        },

        'e_spin_const_y_pulse': {
            'operation': 'control',
            'length': e_spin_const_len,
            'waveforms': {
                # "I": "e_spin_const_wf",
                "I": "zero_wf",
                # "Q": "zero_wf",
                "Q": "e_spin_const_wf"
            },
            'digital_marker': 'ON'
        },

        'gauss_iq_pulse': {
            'operation': "control",
            'length': gauss_len,
            'waveforms': {
                "I": "gauss_wf",
                "Q": "zero_wf"
            },
            'digital_marker': 'ON'
        },

        'X_pulse': {
            'operation': 'control',
            'length': e_spin_X_len,
            'waveforms': {
                'I': 'e_spin_X_wf',
                'Q': 'zero_wf'
            },
            'digital_marker': 'ON'
        },

        'Y_pulse': {
            'operation': 'control',
            'length': e_spin_Y_len,
            'waveforms': {
                'I': 'zero_wf',
                'Q': 'e_spin_Y_wf'
            },
            'digital_marker': 'ON'
        },

        'x_pulse': {
            'operation': "control",
            'length': e_spin_x_len,
            'waveforms': {
                "I": "e_spin_x_wf",
                "Q": "zero_wf"
            },
            'digital_marker': 'ON'
        },

        'reset_pulse': {
            'operation': 'control',
            'length': reset_len,
            'digital_marker': 'ON'
        },

        'n_spin_const_pulse': {
            'operation': 'control',
            'length': n_spin_const_len,
            'waveforms': {'single': 'n_spin_const_wf'},
            'digital_marker': 'ON'
        },

        'trigger_tt_pulse': {
            'operation': 'control',
            'length': tt_len,
            'waveforms': {'single': 'tt_wf'},
            'digital_marker': 'ON'
        },

        'tt_window': {
            'operation': 'control',
            'length': 16,
            'waveforms': {'single': 'zero_wf'},
            'digital_marker': 'ON'
        },

        'res_readout_pulse': {
            'operation': 'control',
            'length': res_read_len,
            'digital_marker': 'ON'
        },

    },

    "waveforms": {

        'zero_wf': {'type': 'constant', 'sample': 0.0},
        'e_spin_const_wf': {'type': 'constant', 'sample': e_spin_const_amp},
        'gauss_wf': {'type': 'arbitrary', 'samples': gauss_wf},
        'tt_wf': {'type': 'arbitrary', 'samples': tt_wf},
        'e_spin_X_wf': {'type': 'arbitrary', 'samples': e_spin_X_wf},
        'e_spin_Y_wf': {'type': 'arbitrary', 'samples': e_spin_Y_wf},
        'e_spin_x_wf': {'type': 'arbitrary', 'samples': e_spin_x_wf},
        'n_spin_const_wf': {'type': 'constant', 'sample': n_spin_const_amp},

    },

    'digital_waveforms': {
        "ON": {
            "samples": [(1, 0)]
        }
    },

    'mixers': {
        'mixer_e_spin': [
            {'intermediate_frequency': e_spin_if_freq, 'lo_frequency': e_spin_lo_freq, 'correction': IQ_imbalance(0., 0.)}],
        }

}


