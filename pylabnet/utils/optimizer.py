import numpy as np
from IPython.display import clear_output
import itertools as it
import pylabnet.hardware.spectrum_analyzer.agilent_e4405B as sa_hardware
import time

import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
from IPython.display import clear_output, display

"""Unnecessary code for instantiating array with desired guess parameters

        init_params is a large 3D array of values with stored starting conditions for carrier in range 11.1 to 13.0 GHz and signal_freq in range 100 MHz to 765 MHz
        User should be able to override init_params array if necessary

        init_params = np.zeros((20,20,5))

        init_params[i, j] => init_params[9,6] => set initial values stored in array
        init_params[9,6]=([60, 0.85, 0.65, 0.005, 0.005])

        Convert to GHz and MHz, respectively, for easier numerical manipulation
	    car = carrier*e-9
        sig = signal_freq*e-6

        indices i and j are calculated from carrier and signal_freq; allows user to access parameters stored in array
        i = 10(round(car,1)-11.1)
        j = round((sig-100)/35)

        self.phase_min = init_params[i,j,0]-10
        self.phase_max = init_params[i,j,0]+10

        self.q_min = init_params[i,j,1]-0.15
        self.q_max = init_params[i,j,1]+0.15

        self.a0_init = init_params[i,j,2]

        self.dc_min_i = init_params[i,j,3]-0.01
        self.dc_max_i = init_params[i,j,3]+0.01
        self.dc_min_q = init_params[i,j,4]-0.01
        self.dc_max_q = init_params[i,j,4]+0.01

Array could be stored externally as text file, but will likely not be necessary"""



class Optimizer:

    def __init__(self):
        pass


class IQOptimizer(Optimizer):
	"""<IQOptimizer planned implementation example:>

	opt1 = IQOptimizer(mw_source, hd, sa, carrier, signal_freq)
	opt1.opt()
	<Sets optimized values using param_guess given (or default param_guess array)>
	<Now, if we want to reoptimize, we run the following:>
	opt1.initialize_reopt_params()
	opt1.opt()
	<This now runs a faster optimization using the parameters collected from the first optimization.>
	"""

	# Constants
	CUSHION_PARAM = 10

	def __init__(
		self, mw_source, hd, sa, carrier, signal_freq, max_lower_sideband_pow = -40, max_carrier_pow = -40, num_points = 25, reopt = False,
		param_guess = ([60, 0.85, 0.65, 0.005, 0.005]), phase_window = 20, q_window = 0.3, dc_i_window = 0.02,
		dc_q_window = 0.02, plot_traces = True
	):
		""" Instantiate IQ optimizer
		:param mw_source: instance of HMC_T2220 client
		:param hd: instance of AWG client
		:param sa: instance of spectrum analyzer client
		:param carrier: desired carrier frequency (in Hz)
		:param signal_freq: desired signal frequency (in Hz)
		:kwarg num_points: number of points for scan window
		:kwarg reopt: dictates whether we want to optimize or reoptimize
		:kwarg plot_traces: user decides if displaying power vs. frequency plots is desired
		"""
		# Configure hd settings
		# Assign oscillator 1 to sine output 2
		hd.seti('sines/1/oscselect', 0)

		# Set carrier frequency
		hd.setd('oscs/0/freq', signal_freq)

		# Set I and Q amplitude, calculate from q and a0 in the param_guess array
		hd.setd('sines/0/amplitudes/0', 2*param_guess[2]*(param_guess[1]/(1+param_guess[1])))
		hd.setd('sines/1/amplitudes/1', 2*param_guess[2]*(1/(1+param_guess[1])))

		# Set phase offset between I and Q
		hd.setd('sines/0/phaseshift', param_guess[0])

		# Enable sine waves
		hd.seti('sines/0/enables/0', 1)
		hd.seti('sines/1/enables/1', 1)


		self.mw_source = mw_source
		self.hd = hd
		self.sa = sa
		self.carrier = carrier
		self.signal_freq = signal_freq
		self.num_points = num_points
		self.reopt = reopt
		self.plot_traces = plot_traces

		#Set mw freq
		self.mw_source.output_on()
		self.mw_source.set_freq(self.carrier)

		#Instantiate IQ Optimizer sweep window
		self.phase_min = param_guess[0]-phase_window/2
		self.phase_max = param_guess[0]+phase_window/2

		self.q_min = param_guess[1]-q_window/2
		self.q_max = param_guess[1]+q_window/2

		self.a0 = param_guess[2]

		self.dc_min_i = param_guess[3]-dc_i_window/2
		self.dc_max_i = param_guess[3]+dc_i_window/2
		self.dc_min_q = param_guess[4]-dc_q_window/2
		self.dc_max_q = param_guess[4]+dc_q_window/2

		# Instantiate params necessary for reoptimization
		self.opt_phase = None
		self.opt_q = None
		self.amp_q_opt = None
		self.amp_i_opt = None
		self.dc_offset_i_opt = None
		self.dc_offset_q_opt = None

		# Instantiate libraries for optimizer values
		self.phases = np.linspace(self.phase_min, self.phase_max, self.num_points)
		self.qs = np.linspace(self.q_min, self.q_max, self.num_points)
		self.lower_sideband_power = np.zeros((self.num_points, self.num_points))
		self.opt_lower_sideband_pow = float("inf")
		self.max_lower_sideband_pow = max_lower_sideband_pow
		self.max_carrier_pow = max_carrier_pow

		# Instantiate and set markers
		self.upp_sb_marker = None
		self.lower_sb_marker = None
		self.carrier_marker = None

		self.set_markers()


	def set_markers(self):

		# Configure hd to enable outputs
		# self.hd.enable_output(0)
		# self.hd.enable_output(1)

		# Center frequency at carrier frequency
		self.sa.set_center_frequency(self.carrier)
		self.sa.set_frequency_span(6*self.signal_freq)
		# Marker for upper sideband.
		self.upp_sb_marker = sa_hardware.E4405BMarker(self.sa,'Upper Sideband',1)
		self.lower_sb_marker = sa_hardware.E4405BMarker(self.sa,'Lower Sideband',2)
		self.carrier_marker = sa_hardware.E4405BMarker(self.sa,'Carrier',3)

		self.upp_sb_marker.look_right()
		self.lower_sb_marker.look_left()

		# define target frequencies
		markers = [self.upp_sb_marker, self.lower_sb_marker, self.carrier_marker]
		target_freqs = np.array([self.carrier + self.signal_freq, self.carrier - self.signal_freq, self.carrier])
		max_deviation = 1e6

		for marker, target_freq in zip(markers, target_freqs):
			time.sleep(1)
			marker_freq = marker.read_freq()

			#assert abs(marker_freq - target_freq) < max_deviation, f"{marker.name} has wrong frequecy: {marker_freq / 1e9} GHz"
			print(f"Marker '{marker.name}' parked at {marker_freq / 1e9:.4f} GHz reads {marker.get_power():.2f} dbm.")

		if self.plot_traces == True:
			self.sa.plot_trace()



	def opt_lower_sideband(self):

		# Rough sweep
		self._sweep_phase_amp_imbalance()
		self._set_optimal_vals()

		# Instantiate variables
		q_max2=self.q_max
		q_min2 = self.q_min
		phase_max2 = self.phase_max
		phase_min2 = self.phase_min

		max_iterations = 3
		num_iterations = 0

		while self.opt_lower_sideband_pow > self.max_lower_sideband_pow and num_iterations < max_iterations:

			q_cushion = np.abs(q_max2-q_min2)/self.CUSHION_PARAM
			phase_cushion = np.abs(phase_max2-phase_min2)/self.CUSHION_PARAM

			# Reset sweep window to zoom in on minimum
			q_max2 = self.opt_q + q_cushion
			q_min2 = self.opt_q - q_cushion
			phase_max2 = self.opt_phase + phase_cushion
			phase_min2 = self.opt_phase - phase_cushion

			# Instantiate variables
			self.phases = np.linspace(phase_min2, phase_max2, self.num_points)
			self.qs = np.linspace(q_min2, q_max2, self.num_points)
			self.lower_sideband_power = np.zeros((self.num_points, self.num_points))

			self._sweep_phase_amp_imbalance()
			self._set_optimal_vals()

			num_iterations = num_iterations + 1
			print(self.opt_lower_sideband_pow)
			time.sleep(5)

		# if self.reopt == False:

		# 	# Finer sweep over portion of phase-amplitude-imbalance space
		# 	q_cushion = self.CUSHION_PARAM*(self.q_max-self.q_min)/self.num_points
		# 	phase_cushion = self.CUSHION_PARAM*(self.phase_max-self.phase_min)/self.num_points

		# 	# Reset sweep window to zoom in on minimum
		# 	q_max2 = self.opt_q + q_cushion
		# 	q_min2 = self.opt_q - q_cushion
		# 	phase_max2 = self.opt_phase + phase_cushion
		# 	phase_min2 = self.opt_phase - phase_cushion

		# 	# Instantiate variables
		# 	self.phases = np.linspace(phase_min2, phase_max2, self.num_points)
		# 	self.qs = np.linspace(q_min2, q_max2, self.num_points)
		# 	self.lower_sideband_power = np.zeros((self.num_points, self.num_points))

		# 	self._sweep_phase_amp_imbalance()
		# 	self._set_optimal_vals()


		if self.plot_traces == True:
			self.sa.plot_trace()


	def opt_carrier(self):

		#DC offset sweep
		carrier_power, voltages_i, voltages_q = self._sweep_dc_offsets()

		# Retrieve optimal DC offsets
		self.dc_offset_i_opt = voltages_i[np.where(carrier_power == np.amin(carrier_power))[0][0]]
		self.dc_offset_q_opt = voltages_q[np.where(carrier_power == np.amin(carrier_power))[1][0]]

		# Set optimal offset
		self.hd.setd('sigouts/0/offset', self.dc_offset_i_opt)
		self.hd.setd('sigouts/1/offset', self.dc_offset_q_opt)

		if self.plot_traces == True:
			self.sa.plot_trace()


	def opt(self):

		self.opt_lower_sideband()
		self.opt_carrier()


	def initialize_reopt_params(
		self, reopt = True, phase_window = 10, q_window = 0.2, dc_i_window = 0.01, dc_q_window = 0.01
	):
		self.param_guess = (
			[self.opt_phase,
			self.opt_q,
			(self.amp_q_opt*self.amp_i_opt) / 2,
			self.dc_offset_i_opt,
			self.dc_offset_q_opt]
		)

		#Introduce error so that markers can be reset
		epsilon3 = 0.003
		epsilon2 = 10
		epsilon1 = 0.001
		# Set optimal I and Q amplitudes
		self.hd.setd('sines/0/amplitudes/0', self.amp_i_opt + epsilon1)
		self.hd.setd('sines/1/amplitudes/1', self.amp_q_opt + epsilon1)

		# Set optimal phaseshift
		self.hd.setd('sines/0/phaseshift', self.opt_phase + epsilon2)

		# Set I DC-offset
		self.hd.setd('sigouts/0/offset', self.dc_offset_i_opt + epsilon3)

		# Set Q DC-offset
		self.hd.setd('sigouts/1/offset', self.dc_offset_q_opt + epsilon3)

		self.reopt = reopt
		self.phase_window = phase_window
		self.q_window =q_window
		self.dc_i_window = dc_i_window
		self.dc_q_window = dc_q_window

		self.set_markers()


	def _sweep_phase_amp_imbalance(self):

		for i, j in it.product(range(self.num_points), repeat=2):

			phase = self.phases[i]
			q = self.qs[j]

			# Calculate amplitudes
			amp_i = 2 * q / (1 + q) * self.a0
			amp_q = 2 * self.a0 / (1 + q)

			# Set I and Q amplitudes
			self.hd.setd('sines/0/amplitudes/0', amp_i)
			self.hd.setd('sines/1/amplitudes/1', amp_q)

			# Set phaseshift
			self.hd.setd('sines/0/phaseshift', phase)

			# Read lower sideband power
			self.lower_sideband_power[i,j] = self.lower_sb_marker.get_power()

			# print(f'{i/self.num_points * 50*2**(int(self.reopt == True))} % done')
			# clear_output(wait=True)


	def _set_optimal_vals(self):

		self.opt_phase = self.phases[np.where(self.lower_sideband_power == np.amin(self.lower_sideband_power))[0][0]]
		self.opt_q = self.qs[np.where(self.lower_sideband_power == np.amin(self.lower_sideband_power))[1][0]]
		self.opt_lower_sideband_pow = np.amin(self.lower_sideband_power)

		self.amp_i_opt = 2 * self.opt_q / (1 + self.opt_q) * self.a0
		self.amp_q_opt = 2 * self.a0 / (1 + self.opt_q)

		# Set optimal I and Q amplitudes
		self.hd.setd('sines/0/amplitudes/0', self.amp_i_opt)
		self.hd.setd('sines/1/amplitudes/1', self.amp_q_opt)

		# Set optimal phaseshift
		self.hd.setd('sines/0/phaseshift', self.opt_phase)

		# Store results in dataframe for easy plotting
		lower_sideband_data = pd.DataFrame(self.lower_sideband_power,
        index=np.round(self.phases, 1),
        columns=np.round(self.qs, 2))
		fig1, ax1 = plt.subplots(figsize=(8, 5))
		ax1 = sns.heatmap(lower_sideband_data, xticklabels=5,  yticklabels=5,  cbar_kws={'label': 'lower sideband power [dBm]'})
		ax1.set(ylabel='Phase shift', xlabel='Amplitude imbalance')
		print(self.opt_phase, self.opt_q)


	def _sweep_dc_offsets(self):

		# Sweep 2D parameter space of DC offsets and record carrier power
		voltages_i = np.linspace(self.dc_min_i, self.dc_max_i, self.num_points)
		voltages_q = np.linspace(self.dc_min_q, self.dc_max_q, self.num_points)

		carrier_power = np.zeros((self.num_points, self.num_points))

		for i, j in it.product(range(self.num_points), repeat=2):

			# Set I DC-offset
			self.hd.setd('sigouts/0/offset', voltages_i[i])

			# Set Q DC-offset
			self.hd.setd('sigouts/1/offset', voltages_q[j])

			# Read carrier power
			carrier_power[i,j] = self.carrier_marker.get_power()
			print(f'{i/self.num_points * 100} % done')
			clear_output(wait=True)

		return carrier_power, voltages_i, voltages_q