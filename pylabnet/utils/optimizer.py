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


class Optimizer:

    def __init__(self):
        pass


class IQOptimizer(Optimizer):

	def __init__(
		self, mw_source, hd, sa, carrier, signal_freq, max_iterations = 5, max_lower_sideband_pow = -55, max_carrier_pow = -55, num_points = 25, cushion_param = 5,
		param_guess = ([60, 0.6, 0.65, -0.002, 0.006]), phase_window = 44, q_window = 0.34, dc_i_window = 0.0135,
		dc_q_window = 0.0115, plot_traces = True
	):
		""" Instantiate IQ optimizer
		:param mw_source: instance of HMC_T2220 client
		:param hd: instance of AWG client
		:param sa: instance of spectrum analyzer client
		:param carrier: desired carrier frequency (in Hz)
		:param signal_freq: desired signal frequency (in Hz)
		:kwarg num_points: number of points for scan window
		:kwarg plot_traces: user decides if displaying power vs. frequency plots is desired
		:kwarg max_iterations: maximum number of iterations to minimize carrier and lower sideband
		:kwarg max_lower_sideband_pow: desired upper bound for lower sideband power (in dBm)
		:kwarg max_carrier_pow: desired upper bound for carrier power (in dBm)
		:kwarg cushion_param: positive real number positively correlated with speed of zooming in on minimum
		:kwarg param_guess: starting parameters for optimization:

		([phase shift, q := (amp_i/amp_q) amplitude imbalance, a0 := (amp_i+amp_q)/2 average amplitude, dc_offset_i, dc_offset_q])

		:kwarg phase_window: size of initial phase scan (in degrees)
		:q_window: size of initial amplitude imbalance scan window (unitless)
		:dc_i_window: size of initial dc i offset scan window (in V)
		:dc_q_window: size of initial dc q offset scan window (in V)
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
		self.max_iterations = max_iterations
		self.plot_traces = plot_traces
		self.cushion_param = cushion_param

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

		# Instantiate params we will optimize
		self.opt_phase = None
		self.opt_q = None
		self.amp_q_opt = None
		self.amp_i_opt = None
		self.dc_offset_i_opt = None
		self.dc_offset_q_opt = None

		# Instantiate arrays and bounds
		self.phases = np.linspace(self.phase_min, self.phase_max, self.num_points)
		self.qs = np.linspace(self.q_min, self.q_max, self.num_points)
		self.lower_sideband_power = np.zeros((self.num_points, self.num_points))
		self.opt_lower_sideband_pow = float("inf")
		self.opt_carrier_pow = float("inf")
		self.max_lower_sideband_pow = max_lower_sideband_pow
		self.max_carrier_pow = max_carrier_pow

		# Instantiate and set markers
		self.upp_sb_marker = None
		self.lower_sb_marker = None
		self.carrier_marker = None

		self.set_markers()


	def set_markers(self):
		#This method is not robust and should be rewritten at some point

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
			self.hd.log.info(f"Marker '{marker.name}' parked at {marker_freq / 1e9:.4f} GHz reads {marker.get_power():.2f} dbm.")

		if self.plot_traces == True:
			self.sa.plot_trace()


	def opt_lower_sideband(self):

		# Rough sweep
		self._sweep_phase_amp_imbalance()
		self._set_optimal_vals()

		# Instantiate local variables for the loop
		q_max2 = self.q_max
		q_min2 = self.q_min
		phase_max2 = self.phase_max
		phase_min2 = self.phase_min

		num_iterations = 0

		while self.opt_lower_sideband_pow > self.max_lower_sideband_pow and num_iterations < self.max_iterations - 1:

			q_cushion = np.abs(q_max2-q_min2)/self.cushion_param
			phase_cushion = np.abs(phase_max2-phase_min2)/self.cushion_param

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

		if num_iterations < self.max_iterations:
			self.hd.log.info('Lower sideband optimization completed in ' + str(num_iterations + 1) + ' iterations')
		else:
			self.hd.log.info('Lower sideband optimization failed to reach threshold in ' + str(num_iterations + 1) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')

		if self.plot_traces == True:
			# Heatmap plot
			lower_sideband_data = pd.DataFrame(self.lower_sideband_power,
			index=np.round(self.phases, 1),
			columns=np.round(self.qs, 2))
			fig1, ax1 = plt.subplots(figsize=(8, 5))
			ax1 = sns.heatmap(lower_sideband_data, xticklabels=5,  yticklabels=5,  cbar_kws={'label': 'lower sideband power [dBm]'})
			ax1.set(ylabel='Phase shift', xlabel='Amplitude imbalance')
			# Frequency plot
			self.sa.plot_trace()


	def opt_carrier(self):

		num_iterations = 0

		# If carrier power already below threshold, no need to optimize carrier
		if self.carrier_marker.get_power() >  self.max_carrier_pow:
			# Sweep 2D parameter space of DC offsets and record carrier power
			voltages_i = np.linspace(self.dc_min_i, self.dc_max_i, self.num_points)
			voltages_q = np.linspace(self.dc_min_q, self.dc_max_q, self.num_points)
			carrier_power = np.zeros((self.num_points, self.num_points))

			dc_max_i2 = self.dc_max_i
			dc_min_i2 = self.dc_min_i
			dc_max_q2 = self.dc_max_q
			dc_min_q2 = self.dc_min_q

			while self.opt_carrier_pow > self.max_carrier_pow and num_iterations < self.max_iterations:

				carrier_power, voltages_i, voltages_q = self._sweep_dc_offsets(voltages_i, voltages_q, carrier_power)

				# Retrieve optimal DC offsets
				self.dc_offset_i_opt = voltages_i[np.where(carrier_power == np.amin(carrier_power))[0][0]]
				self.dc_offset_q_opt = voltages_q[np.where(carrier_power == np.amin(carrier_power))[1][0]]
				self.opt_carrier_pow = np.amin(carrier_power)

				i_cushion = np.abs(dc_max_i2-dc_min_i2)/self.cushion_param
				q_cushion = np.abs(dc_max_q2-dc_min_q2)/self.cushion_param

				# Reset sweep window to zoom in on minimum
				dc_max_i2 = self.dc_offset_i_opt + i_cushion
				dc_min_i2 = self.dc_offset_i_opt - i_cushion
				dc_max_q2 = self.dc_offset_q_opt + q_cushion
				dc_min_q2 = self.dc_offset_q_opt - q_cushion

				# Reinstantiate variables
				voltages_i = np.linspace(dc_min_i2, dc_max_i2, self.num_points)
				voltages_q = np.linspace(dc_min_q2, dc_max_q2, self.num_points)

				num_iterations = num_iterations + 1

			# Set optimal offset
			self.hd.setd('sigouts/0/offset', self.dc_offset_i_opt)
			self.hd.setd('sigouts/1/offset', self.dc_offset_q_opt)

		if num_iterations < self.max_iterations:
			self.hd.log.info('Carrier optimization completed in ' + str(num_iterations) + ' iterations')
		else:
			self.hd.log.info('Carrier optimization failed to reach threshold in ' + str(num_iterations) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()))

		if self.plot_traces == True:
			# Heatmap plot
			dc_sweep_data = pd.DataFrame(carrier_power, columns=np.round(voltages_q/1e-3, 1), index=np.round(voltages_i/1e-3, 1))
			fig, ax = plt.subplots(figsize=(8, 5))
			ax = sns.heatmap(dc_sweep_data, xticklabels=5,  yticklabels=5,  cbar_kws={'label': 'carrier power [dBm]'})
			ax.set(xlabel='DC offset Q signal [mV]', ylabel='DC offset I signal [mV]')
			# Frequency plot
			self.sa.plot_trace()


	def opt(self):

		self.opt_lower_sideband()
		self.opt_carrier()
		time.sleep(1)

		self.hd.log.info('Optimized param_guess is ([' + str(self.opt_phase) + ',' + str(self.opt_q) + ',' + str(.5*(self.amp_q_opt + self.amp_i_opt)) + ',' + str(self.dc_offset_i_opt) + ',' + str(self.dc_offset_q_opt) + '])')
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()) + ' dBm')


	def _sweep_phase_amp_imbalance(self):

		for i, j in it.product(range(self.num_points), repeat=2):

			phase = self.phases[i]
			q = self.qs[j]

			# Calculate i and q amplitudes from q and a0
			amp_i = 2 * q / (1 + q) * self.a0
			amp_q = 2 * self.a0 / (1 + q)

			# Set i and q amplitudes
			self.hd.setd('sines/0/amplitudes/0', amp_i)
			self.hd.setd('sines/1/amplitudes/1', amp_q)

			# Set phaseshift
			self.hd.setd('sines/0/phaseshift', phase)

			# Read lower sideband power
			self.lower_sideband_power[i,j] = self.lower_sb_marker.get_power()


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



	def _sweep_dc_offsets(self,voltages_i, voltages_q ,carrier_power):

		for i, j in it.product(range(self.num_points), repeat=2):

			# Set I DC-offset
			self.hd.setd('sigouts/0/offset', voltages_i[i])

			# Set Q DC-offset
			self.hd.setd('sigouts/1/offset', voltages_q[j])

			# Read carrier power
			carrier_power[i,j] = self.carrier_marker.get_power()

		return carrier_power, voltages_i, voltages_q