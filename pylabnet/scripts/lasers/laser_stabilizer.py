from pylabnet.scripts.pid import PID
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (unpack_launcher, create_server,
    load_config, get_gui_widgets, get_legend_from_graphics_view, add_to_legend)
from pylabnet.utils.logging.logger import LogClient, LogHandler
import pylabnet.hardware.ni_daqs.nidaqmx_card as nidaqmx
import pylabnet.hardware.staticline.staticline as staticline
import pylabnet.network.client_server.nidaqmx_card as nidaqmx_card_server

import numpy as np
import time
import copy
import pickle
import socket
import pyqtgraph as pg


class LaserStabilizer:
    """A class for stabilizing the laser power given a DAQ input, a power control output, and a setpoint"""
    def __init__(self, config='toptica_laser_stabilization'):
        
                # Instantiate GUI
        self.gui = Window(
            gui_template='power_stabilizer',
            host=socket.gethostbyname(socket.gethostname())
        )
        self.widgets = get_gui_widgets(self.gui, p_setpoint=1, p_outputVoltage=1, label_power=1, config=1,
            graph=2, legend=2, clients=1, exp=1, exp_preview=1, configure=1, start=1,
            autosave=1, save_name=1, stop=1, clear=1)

        self.widgets['config'].setText(config)
        self.config = load_config(config, logger=None)

        self.ai_client = nidaqmx_card_server.Client(
            host=self.config["power_input_host"], 
            port=self.config["power_input_port"]
        )

        self.ai_channel = self.config["power_input_channel"]
        
        self.ao_client = nidaqmx_card_server.Client(
            host=self.config["ctrl_output_host"],
            port=self.config["ctrl_output_port"]
        )
        self.ao_channel = self.config["ctrl_output_channel"]
        
        # Configure default parameters
        self.min_voltage = self.config['min_output_voltage']
        self.max_voltage = self.config['max_output_voltage']
        self.gain = self.config['gain']
        self.max_input_voltage =  self.config['max_input_voltage']

        #Loading PID parameters
        self.paramP = self.config["pid"]["p"]
        self.paramI = self.config["pid"]["i"]
        self.paramD = self.config["pid"]["d"]
        self.paramMemory = self.config["memory"]
        self.update_voltageSetpoint()
        self.update_PID()

        self.numReadsPerCycle = self.config["reads_per_cycle"]

        self.curr_output_voltage = self.widgets['p_outputVoltage'].value() #Initializing initial output voltage to 0
        self.widgets['p_outputVoltage'].valueChanged.connect(self._set_output_voltage_from_label)
        self.ao_client.set_ao_voltage(self.ao_channel, self.curr_output_voltage)

        self.last_power_text_update = 0
        self.update_power_label()

        self._initialize_graphs()

        self.widgets['start'].clicked.connect(lambda: self.start(update_vs_gui=True))
        self.widgets['stop'].clicked.connect(self.stop)
        self.widgets['clear'].clicked.connect(lambda: self._clear_data_plots(display_pts=5000))
        self.is_stabilizing = False

    def  _initialize_graphs(self):
        """Initializes a channel and outputs to the GUI

        Should only be called in the initialization of the project
        """
        # Add in teh cleared widgets array
        self.widgets['curve'] = []
        self.widgets['legend'] = [get_legend_from_graphics_view(legend) for legend in self.widgets['legend']]

        # Create curves
        # Power
        self.widgets['curve'].append(self.widgets['graph'][0].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        ))
        add_to_legend(
            legend=self.widgets['legend'][0],
            curve=self.widgets['curve'][0],
            curve_name="Power"
        )

        # Setpoint
        self.widgets['curve'].append(self.widgets['graph'][0].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
        ))
        add_to_legend(
            legend=self.widgets['legend'][0],
            curve=self.widgets['curve'][1],
            curve_name="Setpoint"
        )

        # Clear data
        #self.widgets['clear'][2*index].clicked.connect(
        #    lambda: self.clear_channel(channel)
        #)
        #self.widgets['clear'][2*index+1].clicked.connect(
        #    lambda: self.clear_channel(channel)
        #)


        # Voltage
        self.widgets['curve'].append(self.widgets['graph'][1].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[0])
        ))
        add_to_legend(
            legend=self.widgets['legend'][1],
            curve=self.widgets['curve'][2],
            curve_name="Voltage"
        )

        # Error
        self.widgets['curve'].append(self.widgets['graph'][1].plot(
            pen=pg.mkPen(color=self.gui.COLOR_LIST[1])
        ))
        add_to_legend(
            legend=self.widgets['legend'][1],
            curve=self.widgets['curve'][3],
            curve_name="Error"
        )

        self._clear_data_plots(5000)

    def update_power_label(self):
        currTime = time.time()
        if currTime - self.last_power_text_update > 0.5: 
            power = self.gain*np.array(self.ai_client.get_ai_voltage(self.ai_channel, max_range=self.max_input_voltage))
            self.widgets['label_power'].setText(str(power[-1]))
            self.last_power = power[-1]/self.gain; 
            self.last_power_text_update = currTime
    
    #TODO: Refactor output voltage and label to a getter and setter type thing to keep them consistent
    #Atleast make it less confusing, also could add functionality to set voltage by hand
    def _update_output_voltage_label(self):
        self.widgets['p_outputVoltage'].setValue((self.curr_output_voltage))
        
    def _set_output_voltage_from_label(self):
        if (~self.is_stabilizing): #If we are stabilizing, then the stabilization will trive the value in the box not the other way around
            self.curr_output_voltage = self.widgets['p_outputVoltage'].value()
            self.ao_client.set_ao_voltage(self.ao_channel, self.curr_output_voltage)

    def run(self):
        if self.is_stabilizing:
            self.update_feedback()
            self._update_output_voltage_label()
           
        self.update_plots()
        self.update_power_label()
        
        self.gui.force_update()

    def start(self, update_vs_gui=True, display_pts = 5000):
        """This starts stabilizing the power, set update_vs to False to not update the setpoint from the GUI"""
        if update_vs_gui:
            self.update_voltageSetpoint()
            self._set_output_voltage_from_label()
        
        self.update_PID()


        self._clear_data_plots(display_pts)


        self.is_stabilizing = True
        
        
    def _clear_data_plots(self, display_pts = 5000):
        #Initializing variables for plotting
        self.out_voltages = np.ones(display_pts) * self.curr_output_voltage
        self.measured_powers = np.ones(display_pts) * self.last_power

        # Check that setpoint is reasonable, otherwise set error to 0
        self.errors = np.ones(display_pts) * (self.last_power-self.voltageSetpoint)
        self.sp_data = np.ones(display_pts) * self.voltageSetpoint

    def stop(self):
        """This stops the power stabilization"""
        self.is_stabilizing = False


    def update_voltageSetpoint(self):
        self.voltageSetpoint = self.widgets['p_setpoint'].value()/self.gain
        
    def update_PID(self):
        self.pid = PID(p=self.paramP, i=self.paramI, d=self.paramD, setpoint=self.voltageSetpoint, memory=self.paramMemory)

    def update_feedback(self):
        """ Runs the actual feedback loop"""
        #First read in the current voltage (power)
        #Read in 5 signals (arb) to average
        #TODO: allow user to select reads per signal
        currSignal = self.ai_client.get_ai_voltage(self.ai_channel, self.numReadsPerCycle, max_range=self.max_input_voltage)

        #Add new data to the pid
        self.pid.set_pv(currSignal)

        #Now compute the new control value and update the AO
        self.pid.set_cv()
        self.curr_output_voltage = self.curr_output_voltage + self.pid.cv
        if self.curr_output_voltage < self.min_voltage:
            self.curr_output_voltage = self.min_voltage
        elif self.curr_output_voltage > self.max_voltage:
            self.curr_output_voltage = self.max_voltage


        #Finally updating the analog output
        self.ao_client.set_ao_voltage(self.ao_channel, self.curr_output_voltage)



    def update_plots(self):
            #Adding in new data to plots\
            currSignal = self.ai_client.get_ai_voltage(self.ai_channel, max_range=self.max_input_voltage)
            self.measured_powers = np.append(self.measured_powers[1:], np.mean(currSignal))
            self.out_voltages = np.append(self.out_voltages[1:], self.curr_output_voltage)
            self.errors = np.append(self.errors[1:], (currSignal[-1] - self.voltageSetpoint))
            self.sp_data = np.append(self.sp_data[1:], self.voltageSetpoint)
            #Update power plots
            self.widgets['curve'][0].setData(self.measured_powers*self.gain)
            #Update setpoint plots
            self.widgets['curve'][1].setData(self.sp_data*self.gain)

            # Now update voltage polots
            self.widgets['curve'][2].setData(self.out_voltages)
            self.widgets['curve'][3].setData(self.errors*self.gain)
        
def main():
    laser_stabilizer=LaserStabilizer('toptica_laser_stabilization')
    while True:
        laser_stabilizer.run()
        

if __name__ == '__main__':
    main()
