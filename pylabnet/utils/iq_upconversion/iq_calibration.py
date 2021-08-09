from os import path
import csv
import time
import numpy as np
from pylabnet.utils.iq_upconversion.optimizer import IQOptimizer, IQOptimizer_GD
import pylabnet.utils.iq_upconversion.iq_upconversion_misc as ium
import pylabnet.hardware.awg.zi_hdawg as zi_hdawg

import pyvisa
from pylabnet.utils.logging.logger import LogClient
from pylabnet.network.client_server import agilent_e4405B
import pylabnet.hardware.spectrum_analyzer.agilent_e4405B as sa_hardware


import itertools as it
import pandas as pd

from pylabnet.utils.logging.logger import LogService
from pylabnet.network.core.generic_server import GenericServer
import os
import sys
from pylabnet.utils.iq_upconversion.optimizer import IQOptimizer
from pylabnet.network.client_server import HMC_T2220
from scipy import interpolate
from pylabnet.network.client_server.agilent_83732b import Client


class IQ_Calibration():

	def __init__(self, log=None):
		self.initialized = False
		self.log = log

	def load_calibration(self, filename):
		self.initialized = True

		#First reading in the header info
		with open(filename, 'r', newline='') as cal_file:
			csv_reader = csv.reader(cal_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
			#First manually read in the headers
			lo_powers_row = csv_reader.__next__()
			self.lo_power = float(lo_powers_row[1])
			if_volts_row = csv_reader.__next__()
			self.IF_volt = float(if_volts_row[1])
			#Skipping over the notes parameter
			csv_reader.__next__()

		#Now reading the rest in as a dataframe
		data = pd.read_csv(filename, header=3)
		data = data.set_index([data.columns[0], data.columns[1]])
		self.full_call_data = data
		#We manually unpack each parameter for now, just so its easier to access
		self.q = data.iloc[:, [0]].unstack()
		self.phase = data.iloc[:, [1]].unstack()
		self.dc_i = data.iloc[:, [2]].unstack()
		self.dc_q = data.iloc[:, [3]].unstack()
		self.harms = data.iloc[:, [4,5,6,7,8]]

		#Also loading the harmoincs like that

	def run_calibration(self, filename,  mw_source, hd, sa, lo_low, lo_high, lo_num_points, if_low, if_high, if_num_points, lo_power, if_volts,
		max_iterations = 3, phase_window = 50, q_window = 0.34, dc_i_window = 0.2, dc_q_window = 0.2, plot_traces=False,
		awg_delay_time = 0.01, averages=4, min_rounds=1):
		self.initialized = True

		#Initial setup of the file, including header information
		with open(filename, 'x', newline='') as cal_file:
			csv_writer = csv.writer(cal_file, delimiter=',',
									quotechar='|', quoting=csv.QUOTE_MINIMAL)
			csv_writer.writerow(['LO_Power', str(lo_power)])
			csv_writer.writerow(['IF_volt', str(if_volts)])
			csv_writer.writerow(['Note: '])
			csv_writer.writerow(['LO_F', 'IF_F', 'q', 'phase', 'dc_i', 'dc_q', 'H-1', 'H0', 'H1', 'H2', 'H3'])

		#Now setting up the hardware correctly

		#Initializing HDAWG
		# Select channel grouping
		hd.set_channel_grouping(0)

		hd.enable_output(2)
		hd.enable_output(3)

		#Setting up microwave source
		mw_source.set_power(lo_power)
		mw_source.output_on()

		#Now we are ready to begin our sweep
		lo_frequencies = np.linspace(lo_low, lo_high, lo_num_points)
		if_frequencies = np.linspace(if_low, if_high, if_num_points)

		for i in range(lo_num_points):
			for j in range(if_num_points):
				lo_freq = lo_frequencies[i].item()
				if_freq = if_frequencies[j].item()
				print(":O: " + str(lo_freq/1E9) + " GHz, IF: "  + str(if_freq/1E6) + " MHz")

				t1 = time.time()
				opt = IQOptimizer(mw_source, hd, sa, lo_freq,if_freq,param_guess = ([90, 1, if_volts, -0.002, 0.006]), dc_i_window=dc_i_window, dc_q_window=dc_q_window, awg_delay_time=awg_delay_time, averages=averages,
									min_rounds=min_rounds, max_iterations=max_iterations,  phase_window=phase_window, q_window=q_window, plot_traces=False)
				opt.opt()

				harm = ium.get_power_at_harmonics(sa, lo_freq, if_freq, [-1, 0, 1, 2, 3])
				with open(filename, 'a', newline='') as cal_file:
					csv_writer = csv.writer(cal_file, delimiter=',',
									quotechar='|', quoting=csv.QUOTE_MINIMAL)
					csv_writer.writerow([str(lo_freq), str(if_freq), str(opt.opt_q), str(opt.opt_phase), str(opt.dc_offset_i_opt), str(opt.dc_offset_q_opt), harm[0], harm[1], harm[2], harm[3], harm[4]])
				print(harm)
				print(time.time()-t1)

		#Having writtent he file, load the callibration into memory now
		#We do it this way as opposed to loading the values into memory during the
		#callibraiton so that the matrix construction is only in a single place in the
		#code making it more robust to changes
		self.load_calibration(filename)

	def run_calibration_GD(self, filename,  mw_source, hd, sa,
		lo_low, lo_high, lo_num_points, if_low, if_high, if_num_points, lo_power, if_volts,
		HDAWG_ports=[1,2], oscillator=1,
		max_iterations = 3, plot_traces=False,
		awg_delay_time = 0.01, averages=10, min_rounds=1):
		self.initialized = True

		#Initial setup of the file, including header information
		with open(filename, 'x', newline='') as cal_file:
			csv_writer = csv.writer(cal_file, delimiter=',',
									quotechar='|', quoting=csv.QUOTE_MINIMAL)
			csv_writer.writerow(['LO_Power', str(lo_power)])
			csv_writer.writerow(['IF_volt', str(if_volts)])
			csv_writer.writerow(['Note: '])
			csv_writer.writerow(['LO_F', 'IF_F', 'q', 'phase', 'dc_i', 'dc_q', 'H-1', 'H0', 'H1', 'H2', 'H3'])

		#Now setting up the hardware correctly

		#Initializing HDAWG
		# Select channel grouping
		hd.set_channel_grouping(0)

		hd.enable_output(2)
		hd.enable_output(3)

		#Setting up microwave source
		mw_source.set_power(lo_power)
		mw_source.output_on()

		#Now we are ready to begin our sweep
		lo_frequencies = np.linspace(lo_low, lo_high, lo_num_points)
		if_frequencies = np.linspace(if_low, if_high, if_num_points)

		for i in range(lo_num_points):
			for j in range(if_num_points):
				lo_freq = lo_frequencies[i].item()
				if_freq = if_frequencies[j].item()
				print(":O: " + str(lo_freq/1E9) + " GHz, IF: "  + str(if_freq/1E6) + " MHz")

				t1 = time.time()
				opt = IQOptimizer_GD(mw_source, hd, sa, lo_freq, if_freq,
					param_guess = ([90, 1, 0.75, 0, 0]),
					awg_delay_time=0.01, averages=10, HDAWG_ports=[3,4], oscillator=2,
					min_power=-65, phase_step = 3, vi_step=0.01, vq_step=0.01, max_iterations = 30,
					plot_traces=False)
				opt.opt()

				harm = ium.get_power_at_harmonics(sa, lo_freq, if_freq, [-1, 0, 1, 2, 3])
				with open(filename, 'a', newline='') as cal_file:
					csv_writer = csv.writer(cal_file, delimiter=',',
									quotechar='|', quoting=csv.QUOTE_MINIMAL)
					csv_writer.writerow([str(lo_freq), str(if_freq), str(opt.opt_q), str(opt.opt_phase), str(opt.dc_offset_i_opt), str(opt.dc_offset_q_opt), harm[0], harm[1], harm[2], harm[3], harm[4]])
				print(harm)
				print(time.time()-t1)

		#Having writtent he file, load the callibration into memory now
		#We do it this way as opposed to loading the values into memory during the
		#callibraiton so that the matrix construction is only in a single place in the
		#code making it more robust to changes
		self.load_calibration(filename)

	def get_ampl_phase(self, if_freq, lo_freq):
		if (not self.initialized):
			raise ValueError("No calibration loaded!")
		q_vals = self.q.values
		q_lo = np.array(self.q.index)
		q_if = np.array(self.q.columns.get_level_values(1))
		f = interpolate.interp2d(q_if, q_lo, q_vals)
		q_ret = f(if_freq, lo_freq)

		phase_vals = self.phase.values
		phase_lo = np.array(self.phase.index)
		phase_if = np.array(self.phase.columns.get_level_values(1))
		f = interpolate.interp2d(phase_if, phase_lo, phase_vals)
		phase_ret = f(if_freq, lo_freq)

		return q_ret, phase_ret

	def get_dc_offsets(self, if_freq, lo_freq):
		if (not self.initialized):
			raise ValueError("No calibration loaded!")
		dc_i_vals = self.dc_i.values
		dc_i_lo = np.array(self.dc_i.index)
		dc_i_if = np.array(self.dc_i.columns.get_level_values(1))
		f = interpolate.interp2d(dc_i_if, dc_i_lo, dc_i_vals)
		dc_i_ret = f(if_freq, lo_freq)

		dc_q_vals = self.dc_q.values
		dc_q_lo = np.array(self.dc_q.index)
		dc_q_if = np.array(self.dc_q.columns.get_level_values(1))
		f = interpolate.interp2d(dc_q_if, dc_q_lo, dc_q_vals)
		dc_q_ret = f(if_freq, lo_freq)

		return dc_i_ret, dc_q_ret

	def get_harmonic_powers(self, if_freq, lo_freq):

		if (not self.initialized):
			raise ValueError("No calibration loaded!")

		Hm1 = self.harms.iloc[:, 0].unstack()
		LO = np.array(Hm1.index)
		IF = np.array(Hm1.columns.get_level_values(0))

		h_m1 = Hm1.values
		f = interpolate.interp2d(IF, LO, h_m1)
		h_m1_val = f(if_freq, lo_freq)

		H0 = self.harms.iloc[:, 1].unstack()
		h_0 = H0.values
		f = interpolate.interp2d(IF, LO, h_0)
		h_0_val = f(if_freq, lo_freq)

		H1 = self.harms.iloc[:, 2].unstack()
		h_1 = H1.values
		f = interpolate.interp2d(IF, LO, h_1)
		h_1_val = f(if_freq, lo_freq)

		H2 = self.harms.iloc[:, 3].unstack()
		h_2 = H2.values
		f = interpolate.interp2d(IF, LO, h_2)
		h_2_val = f(if_freq, lo_freq)

		H3 = self.harms.iloc[:, 4].unstack()
		h_3 = H3.values
		f = interpolate.interp2d(IF, LO, h_3)
		h_3_val = f(if_freq, lo_freq)

		return h_m1_val, h_0_val, h_1_val, h_2_val, h_3_val

	def set_optimal_hdawg_values(self, hd, if_freq, lo_freq, HDAWG_ports=[3,4], oscillator=2):
		'''Sets the optimal sine output values on the hdawg for the given IF
		and LO frequencies. Will also set the HDAWG's sine frequency to that
		given by if_freq'''
		if (not self.initialized):
			raise ValueError("No calibration loaded!")
		#Todo: remove same code in the iq_optimizer script and make it a general utility function

		#First setting the desired IF frequency on the HDAWG
		hd.setd('oscs/{}/freq'.format(oscillator-1), if_freq)

		#Computing the optimal I and Q amplitudes
		q_opt, phase_opt = self.get_ampl_phase(if_freq, lo_freq)
		amp_i_opt = 2 * q_opt / (1 + q_opt) * self.IF_volt
		amp_q_opt = 2 * self.IF_volt / (1 + q_opt)

		# Set optimal I and Q amplitudes
		#hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[0]-1), amp_i_opt)
		#hd.setd('sines/{}/amplitudes/1'.format(HDAWG_ports[1]-1), amp_q_opt)

		for port, amp in zip(HDAWG_ports, [amp_i_opt, amp_q_opt]):
					hd.setd(f'awgs/{port//2}/outputs/{port%2}/gains/{port%2}', amp)

		# Set optimal phaseshift
		hd.setd('sines/{}/phaseshift'.format(HDAWG_ports[0]-1), phase_opt)

		# Turn on signals
		hd.seti('sines/{}/enables/0'.format(HDAWG_ports[0]-1), 1)
		hd.seti('sines/{}/enables/1'.format(HDAWG_ports[1]-1), 1)

		# set optimal DC offsets
		dc_i_opt, dc_q_opt = self.get_dc_offsets(if_freq, lo_freq)
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[0]-1), dc_i_opt)
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[1]-1), dc_q_opt)

	def set_optimal_CNOT_values(self, hd, lo_freq, if_freqs=[300e6, 360e6], HDAWG_ports=[3,4], oscillators=[1,2]):
		'''Sets the optimal sine output values on the hdawg for the given IF
		and LO frequencies. Will also set the HDAWG's sine frequency to that
		given by if_freq'''
		if (not self.initialized):
			raise ValueError("No calibration loaded!")
		#Todo: remove same code in the iq_optimizer script and make it a general utility function

		#First CNOT oscillator
		hd.setd('oscs/{}/freq'.format(oscillators[0]-1), if_freqs[0])

		#Second CNOT oscillator
		hd.setd('oscs/{}/freq'.format(oscillators[1]-1), if_freqs[1])

		#Computing the optimal I and Q amplitudes for first CNOT
		q_opt, phase_opt = self.get_ampl_phase(if_freqs[0], lo_freq)
		amp_i_opt = 2 * q_opt / (1 + q_opt) * self.IF_volt
		amp_q_opt = 2 * self.IF_volt / (1 + q_opt)

		# Set optimal I and Q amplitudes for first CNOT
		#hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[0]-1), amp_i_opt)
		#hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[1]-1), amp_q_opt)

		#hd.setd('awgs/0/outputs/0/gains/0'.format(HDAWG_ports[0]-1), amp_i_opt)
		#hd.setd('awgs/1/outputs/0/gains/0'.format(HDAWG_ports[1]-1), amp_q_opt)

		awg1 = int(np.ceil(HDAWG_ports[0]/2))-1
		awg2 = int(np.ceil(HDAWG_ports[1]/2))-1
		out1 = np.mod(HDAWG_ports[0]-1,2)
		out2 = np.mod(HDAWG_ports[1]-1,2)

		hd.setd('awgs/{}/outputs/0/gains/{}'.format(awg1, out1), amp_i_opt)
		hd.setd('awgs/{}/outputs/0/gains/{}'.format(awg2, out2), amp_q_opt)

		# Set optimal phaseshift for first CNOT
		hd.setd('sines/{}/phaseshift'.format(HDAWG_ports[0]-1), phase_opt)

		#Computing the optimal I and Q amplitudes for second CNOT
		q_opt, phase_opt = self.get_ampl_phase(if_freqs[1], lo_freq)
		amp_i_opt = 2 * q_opt / (1 + q_opt) * self.IF_volt
		amp_q_opt = 2 * self.IF_volt / (1 + q_opt)

		# Set optimal I and Q amplitudes for second CNOT
		#hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[0]), amp_i_opt)
		#hd.setd('sines/{}/amplitudes/0'.format(HDAWG_ports[1]), amp_q_opt)

		hd.setd('awgs/{}/outputs/1/gains/{}'.format(awg1, out1), amp_i_opt)
		hd.setd('awgs/{}/outputs/1/gains/{}'.format(awg2, out2), amp_q_opt)

		# Set optimal phaseshift for second CNOT
		hd.setd('sines/{}/phaseshift'.format(HDAWG_ports[0]), phase_opt)

		# set optimal DC offsets
		dc_i_opt, dc_q_opt = self.get_dc_offsets(if_freqs[0], lo_freq) # DC offset mostly depends on lo_freq, not if_freq
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[0]-1), dc_i_opt)
		hd.setd('sigouts/{}/offset'.format(HDAWG_ports[1]-1), dc_q_opt)

	def get_optimal_hdawg_values(self, if_freq, lo_freq):
		'''Gets the optimal sine output values on the hdawg for the given IF
		and LO frequencies.'''
		if (not self.initialized):
			raise ValueError("No calibration loaded!")

		# Computing the optimal I and Q amplitudes
		q_opt, phase_opt = self.get_ampl_phase(if_freq, lo_freq)
		amp_i_opt = 2 * q_opt / (1 + q_opt) * self.IF_volt
		amp_q_opt = 2 * self.IF_volt / (1 + q_opt)

		dc_i_opt, dc_q_opt = self.get_dc_offsets(if_freq, lo_freq)

		return phase_opt, amp_i_opt, amp_q_opt, dc_i_opt, dc_q_opt

	def set_optimal_hdawg_and_LO_values(self, hd, mw_source, freq, HDAWG_ports=[3,4], oscillator=2):
		'''Finds optimal IF and LO frequencies for given output frequency.
		Sets the optimal sine output values on the hdawg for the found IF
		and LO frequencies. Will also set the HDAWG's sine frequency and LO
		frequency to the correct value.'''
		if (not self.initialized):
			raise ValueError("No calibration loaded!")

		LO = np.array(self.phase.index)
		IF = np.array(self.phase.columns.get_level_values(1))

		default_if = 2e6
		default_lo = 12e9

		if freq < LO[0] + IF[0]:
			return default_if, default_lo
			#raise ValueError("Chosen frequency too low!")

		if freq > LO[-1] + IF[-1]:
			return default_if, default_lo
			#raise ValueError("Chosen frequency too high!")

		if_f = np.linspace(LO[0], LO[-1], 100)

		fidelity = []

		for iff in if_f:
			lof = freq-iff
			if lof > LO[0] and lof < LO[-1]:
				hm1, h0, h1, h2, h3 = self.get_harmonic_powers(iff, lof)
				fidelity.append(self.get_fidelity(hm1, h0, h1, h2, h3, iff))
			else:
				fidelity.append(0)

		ii = np.argmax(fidelity)

		mw_source.set_freq(freq-if_f[ii])

		self.set_optimal_hdawg_values(hd, if_f[ii], freq-if_f[ii], HDAWG_ports=HDAWG_ports, oscillator=oscillator)

		return if_f[ii], freq-if_f[ii]

	def get_optimal_hdawg_and_LO_values(self, freq):
		'''Finds optimnal IF and LO frequencies for given output frequency.
		Gets the optimal sine output values on the hdawg for the found IF
		and LO frequencies.'''
		if (not self.initialized):
			raise ValueError("No calibration loaded!")

		LO = np.array(self.phase.index)
		IF = np.array(self.phase.columns.get_level_values(1))

		default_if = 200e6
		default_lo = 12e9
		default_phase_opt = np.array([0])
		default_amp_i_opt = np.array([1])
		default_amp_q_opt = np.array([1])
		default_dc_i_opt = np.array([0])
		default_dc_q_opt = np.array([0])

		if freq < LO[0] + IF[0]:
			return default_if, default_lo, default_phase_opt, default_amp_i_opt, default_amp_q_opt, default_dc_i_opt, default_dc_q_opt
			#raise ValueError("Chosen frequency too low!")

		if freq > LO[-1] + IF[-1]:
			return default_if, default_lo, default_phase_opt, default_amp_i_opt, default_amp_q_opt, default_dc_i_opt, default_dc_q_opt
			#raise ValueError("Chosen frequency too high!")

		if_f = np.linspace(IF[0], IF[-1], 100)

		fidelity = []

		for iff in if_f:
			lof = freq-iff
			if LO[0] < lof < LO[-1]:
				hm1, h0, h1, h2, h3 = self.get_harmonic_powers(iff, lof)
				fidelity.append(self.get_fidelity(hm1, h0, h1, h2, h3, iff))
			else:
				fidelity.append(0)

		ii = np.argmax(fidelity)

		phase_opt, amp_i_opt, amp_q_opt, dc_i_opt, dc_q_opt = self.get_optimal_hdawg_values(if_f[ii], freq-if_f[ii])

		return if_f[ii], freq-if_f[ii], phase_opt, amp_i_opt, amp_q_opt, dc_i_opt, dc_q_opt

	def get_fidelity(self, hm1, h0, h1, h2, h3, iff):
		return 1 - 10**((hm1-h1)/10)/(2*iff) - 10**((h0-h1)/10)/(iff) - 10**((h2-h1)/10)/(iff) - 10**((h3-h1)/10)/(2*iff)

def main():
	mw_client = Client(
		host='192.168.50.104',
		port=25696
	)
	sa = agilent_e4405B.Client(
    	host='localhost',
    	port=12354
	)

	dev_id = 'dev8227'

	#logger = LogClient(
	#	host='140.247.189.50',
	#	port=21861,
	#	module_tag=f'ZI HDAWG {dev_id}'
	#)
	# Instantiate Hardware class
	hd = zi_hdawg.Driver(dev_id, None)

	iq_calibration = IQ_Calibration()
	iq_calibration.run_calibration("results//6_21_2021_cal.csv",  mw_client, hd, sa, 10.4E9,  11.4E9, 11, 100E6, 500E6, 21, 25, 0.75)
	#iq_calibration.run_calibration_GD("results//6_16_2021_cal_w_GD.csv", mw_client, hd, sa, 11.3E9, 12.3E9, 30, 100E6, 500E6, 21, 25, 0.75)

if __name__ == '__main__':
    main()
