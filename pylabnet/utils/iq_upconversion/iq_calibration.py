from os import path
import csv
import time
import numpy as np
from pylabnet.utils.iq_upconversion.optimizer import IQOptimizer
import pylabnet.utils.iq_upconversion.iq_upconversion_misc as ium
import pylabnet.hardware.awg.zi_hdawg as zi_hdawg

import pyvisa
from pylabnet.utils.logging.logger import LogClient
from pylabnet.network.client_server import agilent_e4405B
import pylabnet.hardware.spectrum_analyzer.agilent_e4405B as sa_hardware


import itertools as it
import pandas as pd
import seaborn as sns

from pylabnet.utils.logging.logger import LogService
from pylabnet.network.core.generic_server import GenericServer
import os
import sys
from pylabnet.utils.iq_upconversion.optimizer import IQOptimizer
from pylabnet.network.client_server import HMC_T2220
from scipy import interpolate


class IQ_Calibration():

	def __init__(self):
		self.initialized = False

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

	def get_ampl_phase(self, if_freq, lo_freq):
		if (not self.initialized):
			raise Exception("No calibration loaded!")
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
			raise Exception("No calibration loaded!")
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


	def set_optimal_hdawg_values(self, hd, if_freq, lo_freq):
		'''Sets the optimal sine output values on the hdawg for the given IF
		and LO frequencies. Will also set the HDAWG's sine frequency to that
		given by if_freq'''
		if (not self.initialized):
			raise Exception("No calibration loaded!")
		#Todo: remove same code in the iq_optimizer script and make it a general utility function

		#First setting the desired IF frequency on the HDAWG
		hd.setd('oscs/1/freq', if_freq)

		#Computing the optimal I and Q amplitudes
		q_opt, phase_opt = self.get_ampl_phase(if_freq, lo_freq)
		amp_i_opt = 2 * q_opt / (1 + q_opt) * self.IF_volt
		amp_q_opt = 2 * self.IF_volt / (1 + q_opt)

		# Set optimal I and Q amplitudes
		hd.setd('sines/2/amplitudes/0', amp_i_opt)
		hd.setd('sines/3/amplitudes/1', amp_q_opt)

		# Set optimal phaseshift
		hd.setd('sines/2/phaseshift', phase_opt)

		#Set optimal DC offsets
		dc_i_opt, dc_q_opt = self.get_dc_offsets(if_freq, lo_freq)
		hd.setd('sigouts/2/offset', dc_i_opt)
		hd.setd('sigouts/3/offset', dc_q_opt)
def main():
	mw_client = HMC_T2220.Client(
    	host='140.247.189.82',
    	port=33509
	)
	sa = agilent_e4405B.Client(
    	host='140.247.189.82',
   	 	port=19013
	)

	dev_id = 'dev8227'

	logger = LogClient(
		host='140.247.189.82',
		port=29804,
		module_tag=f'ZI HDAWG {dev_id}'
	)
	# Instantiate Hardware class
	hd = zi_hdawg.Driver(dev_id, logger)

	iq_calibration = IQ_Calibration()
	iq_calibration.run_calibration("1_2_2021_cal.csv", mw_client, hd, sa, 9E9, 12.5E9, 36, 50E6, 500E6, 10, 25, 0.75)
	#iq_calibration.load_calibration("12_25_2020_cal.csv")
	#iq_calibration.get_ampl_phase(150E6, 10E9)
	#iq_calibration.set_optimal_hdawg_values(hd, 150E6, 10E9)

if __name__ == '__main__':
    main()
