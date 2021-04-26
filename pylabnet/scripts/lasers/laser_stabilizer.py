from pylabnet.scripts.pid import PID
from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.helper_methods import (get_ip, unpack_launcher, create_server,
    load_script_config, load_config, get_gui_widgets, get_legend_from_graphics_view, add_to_legend, find_client)
from pylabnet.utils.logging.logger import LogClient, LogHandler
import pylabnet.hardware.ni_daqs.nidaqmx_card as nidaqmx
import pylabnet.hardware.staticline.staticline as staticline
import pylabnet.network.client_server.nidaqmx_card as nidaqmx_card_server

import numpy as np
import time
import copy
import pickle
import pyqtgraph as pg

class LaserStabilizer:
    """A class for stabilizing the laser power given a DAQ input, a power control output, and a setpoint"""
    def __init__(self, config, ao_client=None, ai_client=None, hd=None, check_aom=False, logger=None):
        """Instantiates LaserStabilizer script object for stabilizing the laser
             :param config: (str) name of config file """

        # Instantiate GUI
        self.gui = Window(
            gui_template='power_stabilizer',
            host=get_ip()
        )
        self.widgets = get_gui_widgets(self.gui, p_setpoint=1, p_outputVoltage=1, label_power=1, config=1,
            graph=2, legend=2, hardware_control=1, clear=1, start=1, stop=1)

        self._ao_client = ao_client
        self._ai_client = ai_client
        self._hd = hd
        self.log = logger


        self.config = config
        self.check_aom = check_aom
        self._load_config_file()

        #Now initialize control/output voltage to 0, and set up label
        self._curr_output_voltage = self.widgets['p_outputVoltage'].value() #Stores current output voltage that is outputted by the AO
        self.widgets['p_outputVoltage'].valueChanged.connect(self._set_output_voltage_from_label)
        # self._ao_client.set_ao_voltage(self._ao_channel, self._curr_output_voltage)

        #Update the input power label
        self._last_power_text_update = 0
        self._update_power_label()

        self._initialize_graphs()

        #Setting up hardware power control options
        self.widgets['hardware_control'].enabled = False
        self._under_hardware_control = False
        self.widgets['hardware_control'].toggled.connect(self._update_hardware_control_from_gui)

        #Finally hookup the final buttons
        self.widgets['start'].clicked.connect(lambda: self.start(update_st_gui=True))
        self.widgets['stop'].clicked.connect(self.stop)
        self.widgets['clear'].clicked.connect(lambda: self._clear_data_plots(display_pts=5000))

        #Initially the program starts in the "unlocked" phase
        self._is_stabilizing = False

    def _load_config_file(self):
        """Read values from config file."""

        self._ai_channel = self.config["power_input_channel"]
        self._hwc_ai_channel = self.config['hardware_ctrl_input_channel']
        self._ao_channel = self.config["ctrl_output_channel"]

        # Configure default parameters
        self.min_voltage = self.config['min_output_voltage'] #Minimum output voltage
        self.max_voltage = self.config['max_output_voltage'] #Maximum output voltage
        self.gain = self.config['gain'] #"Gain" between measured voltage and corresponding power
                                        # NOTE: Internally we store all measured powers as the raw voltages
                                        # we then only multiply by the gain factor when displaying
                                        # it to the user.
        self.max_input_voltage =  self.config['max_input_voltage'] #Maximum possible input voltage, used for scaling
                                                                    #the DAQ acquisition range.

        self._hwc_thresh = self.config['hardware_ctrl_thresh']; #Threshold to turn hardware control on/off

        #Loading PID parameters
        self.paramP = self.config["pid"]["p"]
        self.paramI = self.config["pid"]["i"]
        self.paramD = self.config["pid"]["d"]
        self.paramMemory = self.config["memory"] #
        self._update_voltageSetpoint_fromGUI()
        self._update_PID()

        self.numReadsPerCycle = self.config["reads_per_cycle"] #Number of the reads on the DAQ card that are averaged over for an update cycle.

    def check_aom_up(self):
        """Checks if a given HDAWG DIO bit attached to an AOM switch is high"""

        dio_config = load_config('dio_assignment_global')
        DIO_bit = dio_config[self.config["aom_staticline"]]
        current_config = self._hd.geti('dios/0/output')
        DIO_bit_bitshifted =  (0b1 << DIO_bit) # for bit 3: 000...0001000

        DIO_bitup = current_config & DIO_bit_bitshifted

        if DIO_bitup > 0:
            return True
        else:
            return False

    def run(self):
        """Main function to update both teh feedback loop as well as the gui"""

        self._check_hardware_control()

        if self._is_stabilizing:
            #If we are locking the power, then need to update teh feedback loop and change the output label

            # Check if DIO bit is high
            if self.check_aom:
                aom_up = self.check_aom_up()
                if aom_up:
                    self._update_feedback()
                    self._update_output_voltage_label()
            else:
                self._update_feedback()
                self._update_output_voltage_label()

        #We always need to update the plots as well and power label
        self._update_plots()
        self._update_power_label()

        self.gui.force_update()

    def start(self, update_st_gui=True, display_pts = 5000):
        """This method turns on power stabilizationpdate_vs to False to not update the setpoint from the GUI
            :param update_vs_gui: (Boolean) whether the setpoint should be updated based on the value in the gui,
                                Will always be true when start is run in the GUI, but should be false if
                                an external program wishes to start power locking the laser and manually sets the setpoint.
            :param display_pts: (int) number of display points to use in the plots"""
        if update_st_gui:
            #First, update the setpoint based on the text in the GUI
            self._update_voltageSetpoint_fromGUI()
            self._set_output_voltage_from_label()

        #Update hte PID parameters, which will save the new setpoint to the PID object we use
        self._update_PID()

        #Reset the graphs
        self._clear_data_plots(display_pts)

        #Finally turn on the power stabilization
        self._is_stabilizing = True

    def stop(self):
        """This stops power stabilization"""
        self._is_stabilizing = False

    def _update_hardware_control_from_gui(self):
        """Updates hardware_control based on the widget being checked"""
        self._under_hardware_control = self.widgets['hardware_control'].isChecked()

    def _check_hardware_control(self):
        """Method updates whether the program is stabilizing the power or not
        dependent on the status of the voltage at the input port"""
        if self._under_hardware_control:
            v_input = self._ai_client.get_ai_voltage(self._hwc_ai_channel, max_range=10) #CHeck status of hwc voltage input
            v_input = v_input[-1]
            if self._is_stabilizing:
                if v_input < self._hwc_thresh:
                    self.stop()
            else:
                if v_input > self._hwc_thresh:
                    self.start()


    def set_hardware_control(self, value):
        """Allows external program to set hardware control to the value inputed
            :param value: (Boolean) whether hardware control should be turned off or no
            """
        self.widgets['hardware_control'].setChecked(value)
        self._under_hardware_control = value



    def _update_power_label(self):
        """Updates the power reading text on the GUI"""

        #Checks if > 0.5s has elapsed since the last change to the power reading label
        #I do this since otherwise the text label updates too quickly and it's annoying
        #to read.
        currTime = time.time()
        if currTime - self._last_power_text_update > 0.5:
            #If it updates, reads in the power and updates
            #TODO: Read the power in one function only and then all of the places that use it (updating feedback, updating power label, and plotting)
            #access that member variable. Not a huge deal will slightly speed it up I guess and is a bit cleaner.

            power = None

            while power is None:
                try:
                    power = self.gain*np.array(self._ai_client.get_ai_voltage(self._ai_channel, max_range=self.max_input_voltage))
                except:
                    time.sleep(0.01)

            self.widgets['label_power'].setText(str(power[-1]))
            self._last_power = power[-1]/self.gain
            self._last_power_text_update = currTime

    #TODO: Can potentially use some getters/setters to clean up the below two functions make them a little more cllean for the user.
    def _update_output_voltage_label(self):
        """Updates the output voltage label to the current voltage being outputted.
        This is called when the laser is "locked" and the PID loop is actively changing
        the output voltage"""
        self.widgets['p_outputVoltage'].setValue((self._curr_output_voltage))

    def _set_output_voltage_from_label(self):
        """Updates the output control voltage based on the text in the output voltage text box.
        This method is automatically run when the user changes the value in the text box, allowing
        the user to control the output voltage  directly when the laser power is not "locked".
        """
        if (~self._is_stabilizing): #Only updates value if we are not stabilizing, otherwise the PID loop will be driving the output voltage
                                    #as opposed to the user.
            self._curr_output_voltage = self.widgets['p_outputVoltage'].value()
            self._ao_client.set_ao_voltage(self._ao_channel, self._curr_output_voltage)

    def set_control_voltage(self, value):
        """Allows an external program to directly set the control/output voltage in use by the stabilizer
        :param value: (float) value to set output voltage to"""
        self._curr_output_voltage = value
        self._update_output_voltage_label()

    def _update_voltageSetpoint_fromGUI(self):
        """Update the voltage setpoint to whatever value is currently in the setpoint spin box"""
        self.voltageSetpoint = self.widgets['p_setpoint'].value()/self.gain

    def set_setpoint(self, value):
        """Updates the power setpoint, for use by external programs wishing to interface with
        this one.
        :param value: (float) setpoint value to use in units of power (not voltage!)
        NOTE: Using the GUI this is not normally automatically called. Instead the user must
        hit start agian to update the setpoint if they are in the middle of power stabilizing"""
        self.voltageSetpoint = value/self.gain
        self.widgets['p_setpoint'].setValue(value)
        #Need to reset the PID loop with this new setpoint value
        self._update_PID()


    def _update_PID(self):
        """Creates a new PID object based on the current PID member variables to be used for power
        feedbacking"""
        self.pid = PID(p=self.paramP, i=self.paramI, d=self.paramD, setpoint=self.voltageSetpoint, memory=self.paramMemory)

    def _update_feedback(self):
        """ Runs the actual feedback loop"""
        #First read in the current voltage (power)
        #Read in numReadsPerCycle signals (arb) to average
        #TODO: allow user to select reads per signal
        currSignal = None
        while currSignal is None:
            try:
                currSignal = self._ai_client.get_ai_voltage(self._ai_channel, self.numReadsPerCycle, max_range=self.max_input_voltage)
            except:
                time.sleep(0.01)
        #Add new data to the pid
        self.pid.set_pv(np.atleast_1d(np.mean(currSignal)))

        #Now compute the new control value and update the AO
        self.pid.set_cv()
        self._curr_output_voltage = self._curr_output_voltage + self.pid.cv
        if self._curr_output_voltage < self.min_voltage:
            self._curr_output_voltage = self.min_voltage
        elif self._curr_output_voltage > self.max_voltage:
            self._curr_output_voltage = self.max_voltage


        #Finally updating the analog output

        #Do a final check to make sure that if you are in hardware control mode that the voltage control is still HIGH
        #This is to avoid the potential error if the voltage control is toggled low between the last call of _check_hardware_control
        #and update_feedback, whcih would mean that currSignal would be 0 (assuming a pulsed experiment), and causing a garbage
        #feedback which could be an issue in the next pulse.
        if (~self._under_hardware_control): #or self.ai_client.get_ai_voltage(self._hwc_ai_channel)[-1] > self._hwc_thresh):
            self._ao_client.set_ao_voltage(self._ao_channel, self._curr_output_voltage)

    def _clear_data_plots(self, display_pts = 5000):
        """Initializes/clears the variables holding the data which is plotted"""
        #Initializing variables for plotting
        self.out_voltages = np.ones(display_pts) * self._curr_output_voltage
        self.measured_powers = np.ones(display_pts) * self._last_power

        # Check that setpoint is reasonable, otherwise set error to 0
        self.errors = np.ones(display_pts) * (self._last_power-self.voltageSetpoint)
        self.sp_data = np.ones(display_pts) * self.voltageSetpoint

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


    def _update_plots(self):
        """Updates the plots, both by adding in the new data and then drawing the data on the graph"""
        #Adding in new data to plots
        currSignal = None
        while currSignal is None:
            try:
                currSignal = self._ai_client.get_ai_voltage(self._ai_channel, max_range=self.max_input_voltage)
            except:
                time.sleep(0.01)
        self.measured_powers = np.append(self.measured_powers[1:], np.mean(currSignal))
        self.out_voltages = np.append(self.out_voltages[1:], self._curr_output_voltage)
        self.errors = np.append(self.errors[1:], (currSignal[-1] - self.voltageSetpoint))
        self.sp_data = np.append(self.sp_data[1:], self.voltageSetpoint)
        #Update power plots
        self.widgets['curve'][0].setData(self.measured_powers*self.gain)
        #Update setpoint plots
        self.widgets['curve'][1].setData(self.sp_data*self.gain)

        # Now update voltage polots
        self.widgets['curve'][2].setData(self.out_voltages)
        self.widgets['curve'][3].setData(self.errors*self.gain)

class Service(ServiceBase):
    """ A service to enable external updating of LaserStabilizer parameters """
    def exposed_start(self):
        return self._module.start()
    def exposed_stop(self):
        return self._module.stop()
    def exposed_set_control_voltage(self, value):
        return self._module.set_control_voltage(value)
    def exposed_set_setpoint(self, value):
        return self._module.set_setpoint(value)
    def exposed_set_hardware_control(self, value):
        return self._module.set_hardware_control(value)

class Client(ClientBase):
    def start(self):
        return self._service.exposed_start()
    def stop(self):
        return self._service.exposed_stop()
    def set_control_voltage(self, value):
        return self._service.exposed_set_control_voltage(value)
    def set_setpoint(self, value):
        return self._service.exposed_set_setpoint(value)
    def set_hardware_control(self, value):
        return self._service.set_hardware_control(value)

def main():
    laser_stabilizer=LaserStabilizer('toptica_laser_stabilization')
    while True:
        laser_stabilizer.run()

def launch(**kwargs):
    """ Launches the WLM monitor + lock script """


    logger = kwargs['logger']
    clients = kwargs['clients']

    config = load_script_config(script='laser_stabilizer',
                                config=kwargs['config'],
                                logger=logger)
    for server in config['servers']:

        if 'name' in server:
            if server['name'] == 'input':
                ai_client = find_client(
                    clients=clients,
                    settings=config,
                    client_type=server['type'],
                    client_config=server['config'],
                    logger=logger
                )
            if server['name'] == 'output':
                ao_client = find_client(
                    clients=clients,
                    settings=config,
                    client_type=server['type'],
                    client_config=server['config'],
                    logger=logger
                )

        if server['type'] == 'zi_hdawg':
            hd = find_client(
                clients=clients,
                settings=config,
                client_type='zi_hdawg',
                client_config=server['config'],
                logger=logger
            )

    if config['check_aom'] == "True":
        check_aom= True
    else:
        check_aom = False


    # Instantiate Monitor script
    laser_stabilizer = LaserStabilizer(
        config=config,
        ao_client=ao_client,
        ai_client=ai_client,
        hd=hd,
        check_aom = check_aom,
        logger=logger
    )

    update_service = Service()
    update_service.assign_module(module=laser_stabilizer)
    update_service.assign_logger(logger=logger)
    update_server, update_port = create_server(update_service, logger, host=get_ip())
    logger.update_data(data={'port': update_port})
    laser_stabilizer.gui.set_network_info(port=update_port)
    update_server.start()

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        laser_stabilizer.run()


if __name__ == '__main__':
    main()
