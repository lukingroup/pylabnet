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
		self, mw_source, hd, sa, carrier, signal_freq, max_iterations = 5, max_lower_sideband_pow = -65, max_carrier_pow = -65, num_points = 25, cushion_param = 5,
		param_guess = ([60, 0.6, 0.65, -0.002, 0.006]), phase_window = 44, q_window = 0.34, dc_i_window = 0.0135,
		dc_q_window = 0.0115, plot_traces = True, awg_delay_time = 0.0, averages=1, min_rounds=1, HDAWG_ports=[3,4],
		oscillator=2):
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
		#hd.seti('sines/1/oscselect', 1)

		# Set carrier frequency
		hd.setd('oscs/{}/freq'.format(oscillator-1), signal_freq)

		# Set I and Q amplitude, calculate from q and a0 in the param_guess array
		hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[0]-1), 2*param_guess[2]*(param_guess[1]/(1+param_guess[1])))
		hd.setd('sines/{}/amplitudes/1'.format(HDAWG_ports[1]-1), 2*param_guess[2]*(1/(1+param_guess[1])))

		# Set phase offset between I and Q
		hd.setd('sines/{}/phaseshift'.format(HDAWG_ports[0]-1), param_guess[0])

		# Enable sine waves
		hd.seti('sines/{}/enables/0'.format(HDAWG_ports[0]-1), 1)
		hd.seti('sines/{}/enables/1'.format(HDAWG_ports[1]-1), 1)


		self.mw_source = mw_source
		self.hd = hd
		self.sa = sa
		self.carrier = carrier
		self.signal_freq = signal_freq
		self.num_points = num_points
		self.max_iterations = max_iterations
		self.plot_traces = plot_traces
		self.cushion_param = cushion_param

		self.HDAWG_ports = HDAWG_ports

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

		self._AWG_DELAY_TIME = awg_delay_time
		self._averages = averages
		self._min_rounds = min_rounds


	def set_markers(self):
		# Configure hd to enable outputs
		# self.hd.enable_output(0)
		# self.hd.enable_output(1)

		# Center frequency at carrier frequency
		self.sa.set_center_frequency(self.carrier+self.signal_freq)
		self.sa.set_frequency_span(6*self.signal_freq)
		# Marker for upper sideband.
		self.upp_sb_marker = sa_hardware.E4405BMarker(self.sa,'Upper Sideband',1)
		self.lower_sb_marker = sa_hardware.E4405BMarker(self.sa,'Lower Sideband',2)
		self.carrier_marker = sa_hardware.E4405BMarker(self.sa,'Carrier',3)


		# define target frequencies
		markers = [self.upp_sb_marker, self.lower_sb_marker, self.carrier_marker]
		target_freqs = np.array([self.carrier + self.signal_freq, self.carrier - self.signal_freq, self.carrier])
		max_deviation = 1e6

		for marker, target_freq in zip(markers, target_freqs):
			time.sleep(1)
			marker.set_freq(target_freq)

			#assert abs(marker_freq - target_freq) < max_deviation, f"{marker.name} has wrong frequecy: {marker_freq / 1e9} GHz"
			self.hd.log.info(f"Marker '{marker.name}' parked at {target_freq / 1e9:.4f} GHz reads {marker.get_power():.2f} dbm.")

		#Set reference level to just above the height of our signal to minimize our noise floor
		self.sa.set_reference_level(self.upp_sb_marker.get_power() + 2)

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

		while (self.opt_lower_sideband_pow > self.max_lower_sideband_pow or num_iterations < self._min_rounds) and num_iterations < self.max_iterations - 1:

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
		skipped = True
		if self.carrier_marker.get_power() >  (self.max_carrier_pow-10):
			skipped = False
			# Sweep 2D parameter space of DC offsets and record carrier power
			voltages_i = np.linspace(self.dc_min_i, self.dc_max_i, self.num_points)
			voltages_q = np.linspace(self.dc_min_q, self.dc_max_q, self.num_points)
			carrier_power = np.zeros((self.num_points, self.num_points))
			self.opt_carrier_pow = self.carrier_marker.get_power()

			dc_max_i2 = self.dc_max_i
			dc_min_i2 = self.dc_min_i
			dc_max_q2 = self.dc_max_q
			dc_min_q2 = self.dc_min_q

			while (self.opt_carrier_pow > self.max_carrier_pow or num_iterations < self._min_rounds) and num_iterations < self.max_iterations:

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
			self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[0]-1), self.dc_offset_i_opt)
			self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[1]-1), self.dc_offset_q_opt)
			time.sleep(1)
		else:
			print('Skipped Carrier')
			self.dc_offset_i_opt = self.hd.getd('sigouts/{}/offset'.format(self.HDAWG_ports[0]-1))
			self.dc_offset_q_opt = self.hd.getd('sigouts/{}/offset'.format(self.HDAWG_ports[1]-1))

		if num_iterations < self.max_iterations:
			self.hd.log.info('Carrier optimization completed in ' + str(num_iterations) + ' iterations')
		else:
			self.hd.log.info('Carrier optimization failed to reach threshold in ' + str(num_iterations) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()))

		if self.plot_traces == True and not skipped:
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
			self.hd.setd('sines/{}/amplitudes/0'.format(self.HDAWG_ports[0]-1), amp_i)
			self.hd.setd('sines/{}/amplitudes/1'.format(self.HDAWG_ports[1]-1), amp_q)

			# Set phaseshift
			self.hd.setd('sines/{}/phaseshift'.format(self.HDAWG_ports[0]-1), phase)

			#See sweep dc for explanation, basically allowing the point to update
			if (i == 0 and j == 0):
				time.sleep(1)
			if (j == 0):
				time.sleep(0.1)
			else:
				time.sleep(self._AWG_DELAY_TIME)

			# Read lower sideband power

			self.lower_sideband_power[i,j] = self._average_marker_power(self.lower_sb_marker)

	def _average_marker_power(self, marker):
		total_sum = 0
		for i in range(self._averages):
			total_sum = total_sum + marker.get_power()
		return total_sum/self._averages

	def _set_optimal_vals(self):

		self.opt_phase = self.phases[np.where(self.lower_sideband_power == np.amin(self.lower_sideband_power))[0][0]]
		self.opt_q = self.qs[np.where(self.lower_sideband_power == np.amin(self.lower_sideband_power))[1][0]]
		self.opt_lower_sideband_pow = np.amin(self.lower_sideband_power)

		self.amp_i_opt = 2 * self.opt_q / (1 + self.opt_q) * self.a0
		self.amp_q_opt = 2 * self.a0 / (1 + self.opt_q)

		# Set optimal I and Q amplitudes
		self.hd.setd('sines/{}/amplitudes/0'.format(self.HDAWG_ports[0]-1), self.amp_i_opt)
		self.hd.setd('sines/{}/amplitudes/1'.format(self.HDAWG_ports[1]-1), self.amp_q_opt)

		# Set optimal phaseshift
		self.hd.setd('sines/{}/phaseshift'.format(self.HDAWG_ports[0]-1), self.opt_phase)



	def _sweep_dc_offsets(self,voltages_i, voltages_q ,carrier_power):

		for i, j in it.product(range(self.num_points), repeat=2):

			# Set I DC-offset
			self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[0]-1), voltages_i[i])

			# Set Q DC-offset
			self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[1]-1), voltages_q[j])

			# Found a bug where the first few points in the matrix seem to be from the point before, i.e.
			# the script is running faster then the spectrum analyzer can update

			#So we are first going to set the offsets to the initial voltage and wait a bit for teh
			#spectrum analyzer to update

			if (i == 0 and j == 0):
				time.sleep(1)

			#Otherwise just a generic small delay which we empirically have found to work
			if (j == 0):
				time.sleep(0.1)
			else:
				time.sleep(self._AWG_DELAY_TIME)
			# Read carrier power
			carrier_power[i,j] = self._average_marker_power(self.carrier_marker)

		return carrier_power, voltages_i, voltages_q

	def plot_dc_offsets_sweep(self, dc_min_i, dc_max_i, dc_min_q, dc_max_q, num_points):
			voltages_i = np.linspace(dc_min_i, dc_max_i, num_points)
			voltages_q = np.linspace(dc_min_q, dc_max_q, num_points)
			carrier_power = np.zeros((num_points, num_points))

			dc_max_i2 = self.dc_max_i
			dc_min_i2 = self.dc_min_i
			dc_max_q2 = self.dc_max_q
			dc_min_q2 = self.dc_min_q

			carrier_power, voltages_i, voltages_q = self._sweep_dc_offsets(voltages_i, voltages_q, carrier_power)

			dc_sweep_data = pd.DataFrame(carrier_power, columns=np.round(voltages_q/1e-3, 1), index=np.round(voltages_i/1e-3, 1))
			fig, ax = plt.subplots(figsize=(8, 5))
			ax = sns.heatmap(dc_sweep_data, xticklabels=5,  yticklabels=5,  cbar_kws={'label': 'carrier power [dBm]'})
			ax.set(xlabel='DC offset Q signal [mV]', ylabel='DC offset I signal [mV]')

	def plot_phase_amp_sweep(self, phase_min, phase_max, q_min, q_max, num_points):
		self.phases = np.linspace(phase_min, phase_max, num_points)
		self.qs = np.linspace(q_min, q_max, num_points)
		self.lower_sideband_power = np.zeros((num_points, num_points))

		self._sweep_phase_amp_imbalance()

		lower_sideband_data = pd.DataFrame(self.lower_sideband_power,
			index=np.round(self.phases, 1),
			columns=np.round(self.qs, 2))
		fig1, ax1 = plt.subplots(figsize=(8, 5))
		ax1 = sns.heatmap(lower_sideband_data, xticklabels=5,  yticklabels=5,  cbar_kws={'label': 'lower sideband power [dBm]'})
		ax1.set(ylabel='Phase shift', xlabel='Amplitude imbalance')



class IQOptimizer_GD(Optimizer):

	def __init__(
		self, mw_source, hd, sa, carrier, signal_freq, max_iterations = 20, min_power = -65,
		param_guess = ([70, 0.975, 0.65, 0.05, -0.02]), phase_step = 5, q_step = 0.05, vi_step = 0.005, vq_step = 0.005,
		plot_traces = True, awg_delay_time = 0.1, averages=10, HDAWG_ports=[3,4],
		oscillator=2):
		""" Instantiate IQ optimizer
		:param mw_source: instance of microwave source client
		:param hd: instance of AWG client
		:param sa: instance of spectrum analyzer client
		:param carrier: desired carrier frequency (in Hz)
		:param signal_freq: desired signal frequency (in Hz)
		:kwarg plot_traces: user decides if displaying power vs. iteration plots is desired
		:kwarg max_iterations: maximum number of iterations to minimize carrier and lower sideband
		:kwarg min_pow: noise floor
		:kwarg param_guess: starting parameters for optimization:

		([phase shift, q := (amp_i/amp_q) amplitude imbalance, a0 := (amp_i+amp_q)/2 average amplitude, dc_offset_i, dc_offset_q])

		:kwarg phase_step: step size for phase parameter in gradient descent
		:kwarg q_step: step size for amplitude imbalance parameter in gradient descent
		:kwarg vi_step: step size for dc I offset parameter in gradient descent
		:kwarg vq_step: step size for dc Q parameter in gradient descent
		:kwarg awg_delay_time: time to wait after setting awg parameters
		:kwarg averages: number of measurement for single point power measurement
		:kwarg HDAWG_ports: which wave ports to use on the HDAWG
		:kwarg oscillator: which oscillator to use on the HDAWG
		"""

		# Configure hd settings
		# Assign oscillator 1 to sine output 2
		#hd.seti('sines/1/oscselect', 1)

		# Set carrier frequency
		hd.setd('oscs/{}/freq'.format(oscillator-1), signal_freq)

		# Set I and Q amplitude, calculate from q and a0 in the param_guess array
		hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[0]-1), 2*param_guess[2]*(param_guess[1]/(1+param_guess[1])))
		hd.setd('sines/{}/amplitudes/1'.format(HDAWG_ports[1]-1), 2*param_guess[2]*(1/(1+param_guess[1])))

		# Set phase offset between I and Q
		hd.setd('sines/{}/phaseshift'.format(HDAWG_ports[0]-1), param_guess[0])

		# Enable sine waves
		hd.seti('sines/{}/enables/0'.format(HDAWG_ports[0]-1), 1)
		hd.seti('sines/{}/enables/1'.format(HDAWG_ports[1]-1), 1)

		# set DC offsets
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[0]-1), param_guess[3])
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[1]-1), param_guess[4])


		self.mw_source = mw_source
		self.hd = hd
		self.sa = sa
		self.carrier = carrier
		self.signal_freq = signal_freq
		self.max_iterations = max_iterations
		self.plot_traces = plot_traces
		self.min_power = min_power

		self.HDAWG_ports = HDAWG_ports

		#Set mw freq
		self.mw_source.output_on()
		self.mw_source.set_freq(self.carrier)

		#Instantiate step sizes
		self.phase_step = phase_step
		self.q_step = q_step
		self.vi_step = vi_step
		self.vq_step = vq_step

		#Instantiate initial guesses
		self.phase_guess = param_guess[0]
		self.q_guess = param_guess[1]
		self.a0 = param_guess[2]

		self.dc_i_guess = param_guess[3]
		self.dc_q_guess = param_guess[4]

		# Instantiate params we will optimize
		self.opt_phase = None
		self.opt_q = None
		self.amp_q_opt = None
		self.amp_i_opt = None
		self.dc_offset_i_opt = None
		self.dc_offset_q_opt = None

		# Instantiate arrays and bounds
		self.opt_lower_sideband_pow = float("inf")
		self.opt_carrier_pow = float("inf")

		# Instantiate and set markers
		self.upp_sb_marker = None
		self.lower_sb_marker = None
		self.carrier_marker = None

		self.set_markers()

		self._AWG_DELAY_TIME = awg_delay_time
		self._averages = averages


	def set_markers(self):
		# Configure hd to enable outputs
		# self.hd.enable_output(0)
		# self.hd.enable_output(1)

		# Center frequency at carrier frequency
		self.sa.set_center_frequency(self.carrier+self.signal_freq)
		self.sa.set_frequency_span(6*self.signal_freq)
		# Marker for upper sideband.
		self.upp_sb_marker = sa_hardware.E4405BMarker(self.sa,'Upper Sideband',1)
		self.lower_sb_marker = sa_hardware.E4405BMarker(self.sa,'Lower Sideband',2)
		self.carrier_marker = sa_hardware.E4405BMarker(self.sa,'Carrier',3)


		# define target frequencies
		markers = [self.upp_sb_marker, self.lower_sb_marker, self.carrier_marker]
		target_freqs = np.array([self.carrier + self.signal_freq, self.carrier - self.signal_freq, self.carrier])
		max_deviation = 1e6

		for marker, target_freq in zip(markers, target_freqs):
			time.sleep(1)
			marker.set_freq(target_freq)

			#assert abs(marker_freq - target_freq) < max_deviation, f"{marker.name} has wrong frequecy: {marker_freq / 1e9} GHz"
			self.hd.log.info(f"Marker '{marker.name}' parked at {target_freq / 1e9:.4f} GHz reads {marker.get_power():.2f} dbm.")

		#Set reference level to just above the height of our signal to minimize our noise floor
		self.sa.set_reference_level(self.upp_sb_marker.get_power() + 2)

		if self.plot_traces == True:
			self.sa.plot_trace()


	def opt_lower_sideband(self):

		#gradient descent starting point
		phase = self.phase_guess
		q = self.q_guess

		self.set_phase_and_amp(phase, q)
		curr_power = self._average_marker_power(self.lower_sb_marker)

		#store power values for every iteration
		power_vec = [curr_power]

		#initialize step sizes and iteration number
		phase_step = self.phase_step
		q_step = self.q_step
		num_iterations = 0

		while num_iterations < self.max_iterations and curr_power > self.min_power:

			grad = self.calc_slope_phase_and_amp(phase, q, phase_step, q_step)

			phase_new = phase - grad[0] * phase_step
			q_new = q - grad[1] * q_step

			self.set_phase_and_amp(phase_new, q_new)
			new_power = self._average_marker_power(self.lower_sb_marker)

			if new_power < curr_power:
				curr_power = new_power
				phase = phase_new
				q = q_new
			else:
				phase_step = phase_step/2
				q_step = q_step/2

			power_vec.append(curr_power)

			num_iterations = num_iterations + 1

		if num_iterations < self.max_iterations:
			self.hd.log.info('Lower sideband optimization completed in ' + str(num_iterations + 1) + ' iterations')
		else:
			self.hd.log.info('Lower sideband optimization failed to reach threshold in ' + str(num_iterations + 1) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')

		self.opt_phase = phase
		self.opt_q = q
		self.set_phase_and_amp(self.opt_phase, self.opt_q)
		self.lower_sideband_power = self.lower_sb_marker.get_power()

		if self.plot_traces == True:
			plt.plot(power_vec, label='lower band')

	def opt_carrier(self):

		#gradient descent starting point
		vi = self.dc_i_guess
		vq = self.dc_q_guess

		self.set_dc_offsets(vi, vq)
		curr_power = self._average_marker_power(self.carrier_marker)

		#store power values for every iteration
		power_vec = [curr_power]

		# initialize step sizes and iteration number
		vi_step = self.vi_step
		vq_step = self.vq_step
		num_iterations = 0

		while num_iterations < self.max_iterations and curr_power > self.min_power:

			grad = self.calc_slope_dc_offsets(vi, vq, vi_step, vq_step)

			vi_new = vi - grad[0] * vi_step
			vq_new = vq - grad[1] * vq_step

			self.set_dc_offsets(vi_new, vq_new)
			new_power = self._average_marker_power(self.carrier_marker)

			if new_power < curr_power:
				curr_power = new_power
				vi = vi_new
				vq = vq_new
			else:
				vi_step = vi_step/1.2
				vq_step = vq_step/1.2

			power_vec.append(curr_power)

			num_iterations = num_iterations + 1

		if num_iterations < self.max_iterations:
			self.hd.log.info('Carrier optimization completed in ' + str(num_iterations) + ' iterations')
		else:
			self.hd.log.info('Carrier optimization failed to reach threshold in ' + str(num_iterations) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()) + 'dBm')

		self.dc_offset_i_opt = vi
		self.dc_offset_q_opt =  vq
		self.set_dc_offsets(self.dc_offset_i_opt, self.dc_offset_q_opt)
		self.carrier_power = self.carrier_marker.get_power()

		if self.plot_traces == True:
			plt.plot(power_vec, label='carrier band')
			plt.xlabel('iteration #')
			plt.ylabel('power [dBm]')
			plt.legend()


	def opt(self):

		self.opt_lower_sideband()
		while self.lower_sideband_power > self.min_power + 7.5:
			self.opt_lower_sideband()
		self.opt_carrier()
		while self.carrier_power > self.min_power + 7.5:
			self.dc_i_guess = self.dc_offset_i_opt
			self.dc_q_guess = self.dc_offset_q_opt
			self.opt_carrier()

		#for i in range(10):
		#	if self.carrier_power - 3.5 > self.lower_sideband_power:
		#		self.dc_i_guess = self.dc_offset_i_opt
		#		self.dc_q_guess = self.dc_offset_q_opt
		#		self.opt_carrier()

		time.sleep(1)

		self.hd.log.info('Optimized param_guess is ([' + str(self.opt_phase) + ',' + str(self.opt_q) + ',' + str(self.a0) + ',' + str(self.dc_offset_i_opt) + ',' + str(self.dc_offset_q_opt) + '])')
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()) + ' dBm')

	def set_phase_and_amp(self, phase, q):
		amp_i = 2 * q / (1 + q) * self.a0
		amp_q = 2 * self.a0 / (1 + q)

		# Set i and q amplitudes
		self.hd.setd('sines/{}/amplitudes/0'.format(self.HDAWG_ports[0]-1), amp_i)
		self.hd.setd('sines/{}/amplitudes/1'.format(self.HDAWG_ports[1]-1), amp_q)

		# Set phaseshift
		self.hd.setd('sines/{}/phaseshift'.format(self.HDAWG_ports[0]-1), phase)

	def set_dc_offsets(self, v1, v2):
		# Set I DC-offset
		self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[0]-1), v1)

		# Set Q DC-offset
		self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[1]-1), v2)

	def _average_marker_power(self, marker):
		total_sum = 0
		for i in range(self._averages):
			total_sum = total_sum + marker.get_power()
		return total_sum/self._averages

	def calc_slope_phase_and_amp(self, phase, q, phase_step, q_step):
		self.set_phase_and_amp(phase + phase_step, q)
		phase_p = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase - phase_step, q)
		phase_m = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase, q + q_step)
		q_p = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase, q - q_step)
		q_m = self._average_marker_power(self.lower_sb_marker)

		return([(phase_p-phase_m)/2, (q_p-q_m)/2])

	def calc_slope_dc_offsets(self, vi, vq, vi_step, vq_step):
		self.set_dc_offsets(vi + vi_step, vq)
		vi_p = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi - vi_step, vq)
		vi_m = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi, vq + vq_step)
		vq_p = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi, vq - vq_step)
		vq_m = self._average_marker_power(self.carrier_marker)

		return([(vi_p-vi_m)/2, (vq_p-vq_m)/2])



class IQOptimizer_GD_multifreq(Optimizer):

	def __init__(
		self, mw_source, hd, sa, carrier, signal_freq, max_iterations = 20, min_power = -65,
		param_guess = ([85, 85, 0.9, 0.9, 0.05, -0.02]), phase_step = 5, q_step = 0.1, vi_step = 0.005, vq_step = 0.005,
		plot_traces = True, awg_delay_time = 0.1, averages=5, HDAWG_ports=[3,4],
		oscillator=[1,2]):

		""" Instantiate IQ optimizer
		:param mw_source: instance of microwave source client
		:param hd: instance of AWG client
		:param sa: instance of spectrum analyzer client
		:param carrier: desired carrier frequency (in Hz)
		:param signal_freq: desired signal frequencies
		:kwarg plot_traces: user decides if displaying power vs. iteration plots is desired
		:kwarg max_iterations: maximum number of iterations to minimize carrier and lower sideband
		:kwarg min_pow: noise floor
		:kwarg param_guess: starting parameters for optimization:

		([phase shift 1, phase shift 2,
			q := (amp_i/amp_q) amplitude imbalance 1, amplitude imbalance 2
			dc_offset_i, dc_offset_q])

		:kwarg phase_step: step size for phase parameter in gradient descent
		:kwarg q_step: step size for amplitude imbalance parameter in gradient descent
		:kwarg vi_step: step size for dc I offset parameter in gradient descent
		:kwarg vq_step: step size for dc Q parameter in gradient descent
		:kwarg awg_delay_time: time to wait after setting awg parameters
		:kwarg averages: number of measurement for single point power measurement
		:kwarg HDAWG_ports: which wave ports to use on the HDAWG
		:kwarg oscillator: which oscillator to use on the HDAWG
		"""

		# Set carrier frequency
		hd.setd('oscs/{}/freq'.format(oscillator[0]-1), signal_freq[0])
		hd.setd('oscs/{}/freq'.format(oscillator[1]-1), signal_freq[1])

		# assign oscillators to correct outputs
		# for first output
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/0/oscselect'.format(
			int(np.floor((HDAWG_ports[0]-1)/2)),
			np.mod(HDAWG_ports[0]-1,2)),
			oscillator[0]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/1/oscselect'.format(
			int(np.floor((HDAWG_ports[0]-1)/2)),
			np.mod(HDAWG_ports[0]-1,2)),
			oscillator[0]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/2/oscselect'.format(
			int(np.floor((HDAWG_ports[0]-1)/2)),
			np.mod(HDAWG_ports[0]-1,2)),
			oscillator[1]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/3/oscselect'.format(
			int(np.floor((HDAWG_ports[0]-1)/2)),
			np.mod(HDAWG_ports[0]-1,2)),
			oscillator[1]-1)
			# for second output
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/0/oscselect'.format(
			int(np.floor((HDAWG_ports[1]-1)/2)),
			np.mod(HDAWG_ports[1]-1,2)),
			oscillator[0]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/1/oscselect'.format(
			int(np.floor((HDAWG_ports[1]-1)/2)),
			np.mod(HDAWG_ports[1]-1,2)),
			oscillator[0]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/2/oscselect'.format(
			int(np.floor((HDAWG_ports[1]-1)/2)),
			np.mod(HDAWG_ports[1]-1,2)),
			oscillator[1]-1)
		hd.seti('awgs/{}/outputs/{}/modulation/carriers/3/oscselect'.format(
			int(np.floor((HDAWG_ports[1]-1)/2)),
			np.mod(HDAWG_ports[1]-1,2)),
			oscillator[1]-1)

		self.mw_source = mw_source
		self.hd = hd
		self.sa = sa
		self.carrier = carrier
		self.signal_freq = signal_freq
		self.max_iterations = max_iterations
		self.plot_traces = plot_traces
		self.min_power = min_power

		self.HDAWG_ports = HDAWG_ports

		#Set mw freq
		self.mw_source.output_on()
		self.mw_source.set_freq(self.carrier)

		#Instantiate step sizes
		self.phase_step = phase_step
		self.q_step = q_step
		self.vi_step = vi_step
		self.vq_step = vq_step

		#Instantiate initial guesses
		self.phase_guess = [param_guess[0], param_guess[1]]
		self.q_guess = [param_guess[2], param_guess[3]]

		self.dc_i_guess = param_guess[4]
		self.dc_q_guess = param_guess[5]

		# Instantiate params we will optimize
		self.opt_phase = np.zeros(2)
		self.opt_q = np.zeros(2)
		self.amp_q_opt = None
		self.amp_i_opt = None
		self.dc_offset_i_opt = None
		self.dc_offset_q_opt = None

		# Instantiate arrays and bounds
		self.opt_lower_sideband_pow = float("inf")
		self.opt_carrier_pow = float("inf")

		# Instantiate and set markers
		self.upp_sb_marker = None
		self.lower_sb_marker = None
		self.carrier_marker = None

		# set initial guess parameters
		self.set_phase_and_amp(self.phase_guess[0], self.q_guess[0], 0)
		self.set_phase_and_amp(self.phase_guess[1], self.q_guess[1], 1)
		self.set_dc_offsets(self.dc_i_guess, self.dc_q_guess)

		# Enable signal
		self.hd.seti('awgs/{}/enable'.format(int(np.floor((HDAWG_ports[1]-1)/2))), 1)

		self.set_markers(1)

		self._AWG_DELAY_TIME = awg_delay_time
		self._averages = averages


	def set_markers(self, signal):
		# signal: 0 or 1, refers two first or second frequency

		# Center frequency at carrier frequency
		self.sa.set_center_frequency(self.carrier+self.signal_freq[signal])
		self.sa.set_frequency_span(6*self.signal_freq[signal])
		# Marker for upper sideband.
		self.upp_sb_marker = sa_hardware.E4405BMarker(self.sa,'Upper Sideband',1)
		self.lower_sb_marker = sa_hardware.E4405BMarker(self.sa,'Lower Sideband',2)
		self.carrier_marker = sa_hardware.E4405BMarker(self.sa,'Carrier',3)


		# define target frequencies
		markers = [self.upp_sb_marker, self.lower_sb_marker, self.carrier_marker]
		target_freqs = np.array([self.carrier + self.signal_freq[signal], self.carrier - self.signal_freq[signal], self.carrier])
		max_deviation = 1e6

		for marker, target_freq in zip(markers, target_freqs):
			time.sleep(1)
			marker.set_freq(target_freq)

			#assert abs(marker_freq - target_freq) < max_deviation, f"{marker.name} has wrong frequecy: {marker_freq / 1e9} GHz"
			self.hd.log.info(f"Marker '{marker.name}' parked at {target_freq / 1e9:.4f} GHz reads {marker.get_power():.2f} dbm.")

		#Set reference level to just above the height of our signal to minimize our noise floor
		self.sa.set_reference_level(self.upp_sb_marker.get_power() + 2)

		if self.plot_traces == True:
			self.sa.plot_trace()


	def opt_lower_sideband(self, signal):

		#set the markers for the sideband we are currently looking at
		if self.plot_traces == True:
			self.plot_traces = False
			self.set_markers(signal)
			self.plot_traces = True
		else:
			self.set_markers(signal)

		#gradient descent starting point
		phase = self.phase_guess[signal]
		q = self.q_guess[signal]

		self.set_phase_and_amp(phase, q, signal)
		curr_power = self._average_marker_power(self.lower_sb_marker)

		#store power values for every iteration
		power_vec = [curr_power]

		# initialize step sizes and iteration number
		num_iterations = 0
		phase_step = self.phase_step
		q_step = self.q_step

		while num_iterations < self.max_iterations and curr_power > self.min_power:

			grad = self.calc_slope_phase_and_amp(phase, q, signal, phase_step, q_step)

			phase_new = phase - grad[0] * phase_step
			q_new = q - grad[1] * q_step

			self.set_phase_and_amp(phase_new, q_new, signal)
			new_power = self._average_marker_power(self.lower_sb_marker)

			if new_power < curr_power:
				curr_power = new_power
				phase = phase_new
				q = q_new
			else:
				phase_step = phase_step/2
				q_step = q_step/2

			power_vec.append(curr_power)

			num_iterations = num_iterations + 1

		if num_iterations < self.max_iterations:
			self.hd.log.info('Lower sideband optimization completed in ' + str(num_iterations + 1) + ' iterations')
		else:
			self.hd.log.info('Lower sideband optimization failed to reach threshold in ' + str(num_iterations + 1) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')

		self.opt_phase[signal] = phase
		self.opt_q[signal] = q
		self.set_phase_and_amp(self.opt_phase[signal], self.opt_q[signal], signal)

		if self.plot_traces == True:
			plt.plot(power_vec, label='lower sideband for frequency {}'.format(signal))


	def opt_carrier(self):

		#gradient descent starting point
		vi = self.dc_i_guess
		vq = self.dc_q_guess

		self.set_dc_offsets(vi, vq)
		curr_power = self._average_marker_power(self.carrier_marker)

		#store power values for every iteration
		power_vec = [curr_power]

		num_iterations = 0

		while num_iterations < self.max_iterations and curr_power > self.min_power:

			grad = self.calc_slope_dc_offsets(vi, vq)

			vi_new = vi - grad[0] * self.vi_step
			vq_new = vq - grad[1] * self.vq_step

			self.set_dc_offsets(vi_new, vq_new)
			new_power = self._average_marker_power(self.carrier_marker)

			if new_power < curr_power:
				curr_power = new_power
				vi = vi_new
				vq = vq_new
			else:
				self.vi_step = self.vi_step/1.2
				self.vq_step = self.vq_step/1.2

			power_vec.append(curr_power)

			num_iterations = num_iterations + 1

		if num_iterations < self.max_iterations:
			self.hd.log.info('Carrier optimization completed in ' + str(num_iterations) + ' iterations')
		else:
			self.hd.log.info('Carrier optimization failed to reach threshold in ' + str(num_iterations) +  ' iterations')

		time.sleep(1)
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()) + 'dBm')

		self.dc_offset_i_opt = vi
		self.dc_offset_q_opt =  vq
		self.set_dc_offsets(self.dc_offset_i_opt, self.dc_offset_q_opt)

		if self.plot_traces == True:
			plt.plot(power_vec, label='carrier band')
			plt.xlabel('iteration #')
			plt.ylabel('power [dBm]')
			plt.legend()

	def opt(self):

		self.opt_lower_sideband(0)
		self.hd.log.info('Lower sideband power for 1st frequency is ' + str(self.lower_sb_marker.get_power()) + ' dBm')
		self.opt_lower_sideband(1)
		self.hd.log.info('Lower sideband power for second frequency is ' + str(self.lower_sb_marker.get_power()) + ' dBm')
		self.opt_carrier()
		time.sleep(1)

		#self.hd.log.info('Optimized param_guess is ([' + str(self.opt_phase) + ',' + str(self.opt_q) + ',' + str(self.a0) + ',' + str(self.dc_offset_i_opt) + ',' + str(self.dc_offset_q_opt) + '])')
		self.hd.log.info('Lower sideband power is ' + str(self.lower_sb_marker.get_power()) + ' dBm')
		self.hd.log.info('Carrier power is ' + str(self.carrier_marker.get_power()) + ' dBm')

	def set_phase_and_amp(self, phase, q, signal):
		amp_i = 2. * q / (1 + q)
		amp_q = 2. * 1 / (1 + q)

		dphase_i = np.arccos(amp_i/2) * 180 / np.pi
		dphase_q = np.arccos(amp_q/2) * 180 /np.pi

		# Set i and q amplitudes
		self.hd.setd('awgs/{}/outputs/{}/modulation/carriers/{}/phaseshift'.format(
			int(np.floor((self.HDAWG_ports[0]-1)/2)),
			np.mod(self.HDAWG_ports[0]-1,2),
			2*signal), phase+dphase_i)
		self.hd.setd('awgs/{}/outputs/{}/modulation/carriers/{}/phaseshift'.format(
			int(np.floor((self.HDAWG_ports[0]-1)/2)),
			np.mod(self.HDAWG_ports[0]-1,2),
			2*signal+1), phase-dphase_i)
		self.hd.setd('awgs/{}/outputs/{}/modulation/carriers/{}/phaseshift'.format(
			int(np.floor((self.HDAWG_ports[1]-1)/2)),
			np.mod(self.HDAWG_ports[1]-1,2),
			2*signal), dphase_q)
		self.hd.setd('awgs/{}/outputs/{}/modulation/carriers/{}/phaseshift'.format(
			int(np.floor((self.HDAWG_ports[1]-1)/2)),
			np.mod(self.HDAWG_ports[1]-1,2),
			2*signal+1), -dphase_q)

	def set_dc_offsets(self, v1, v2):
		# Set I DC-offset
		self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[0]-1), v1)

		# Set Q DC-offset
		self.hd.setd('sigouts/{}/offset'.format(self.HDAWG_ports[1]-1), v2)

	def _average_marker_power(self, marker):
		total_sum = 0
		for i in range(self._averages):
			total_sum = total_sum + marker.get_power()
		return total_sum/self._averages

	def calc_slope_phase_and_amp(self, phase, q, signal, phase_step, q_step):
		self.set_phase_and_amp(phase + phase_step, q, signal)
		phase_p = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase - phase_step, q, signal)
		phase_m = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase, q + q_step, signal)
		q_p = self._average_marker_power(self.lower_sb_marker)

		self.set_phase_and_amp(phase, q - q_step, signal)
		q_m = self._average_marker_power(self.lower_sb_marker)

		return([(phase_p-phase_m)/2, (q_p-q_m)/2])

	def calc_slope_dc_offsets(self, vi, vq):
		self.set_dc_offsets(vi + self.vi_step, vq)
		vi_p = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi - self.vi_step, vq)
		vi_m = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi, vq + self.vq_step)
		vq_p = self._average_marker_power(self.carrier_marker)

		self.set_dc_offsets(vi, vq - self.vq_step)
		vq_m = self._average_marker_power(self.carrier_marker)

		return([(vi_p-vi_m)/2, (vq_p-vq_m)/2])