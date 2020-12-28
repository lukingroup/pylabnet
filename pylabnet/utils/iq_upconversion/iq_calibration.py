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

class IQ_Calibration():

	def __init__(self):
		self.initialized = False

	def load_calibration(self, filename):
		self.initialized = True
		print("not implemented yet")

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
			csv_writer.writerow([['LO_F', 'IF_F', 'q', 'phase', 'dc_i', 'dc_q', 'H-1', 'H0', 'H1', 'H2', 'H3']])	

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
		

	def get_dc_offsets(self, if_freq, lo_freq):
		if (not self.initialized):
			raise Exception("No calibration loaded!")

def main():
	mw_client = HMC_T2220.Client(
    	host='localhost',
    	port=12378
	)
	sa = agilent_e4405B.Client(
    	host='localhost',
   	 	port=12352
	)

	dev_id = 'dev8227'

	logger = LogClient(
		host='140.247.189.82',
		port=48524,
		module_tag=f'ZI HDAWG {dev_id}'
	)
	# Instantiate Hardware class
	hd = zi_hdawg.Driver(dev_id, logger)

	iq_calibration = IQ_Calibration()
	iq_calibration.run_calibration("12_25_2020_cal.csv", mw_client, hd, sa, 9E9, 12.5E9, 36, 50E6, 500E6, 10, 25, 0.75)


if __name__ == '__main__':
    main()
