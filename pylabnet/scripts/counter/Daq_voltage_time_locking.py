""" Generic script for monitoring counts from a counter """

import numpy as np
import time
import pyqtgraph as pg
from pylabnet.gui.pyqt.external_gui import Window
from pylabnet.utils.logging.logger import LogClient
from pylabnet.scripts.pause_script import PauseService
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server import si_tt, nidaqmx_card
from pylabnet.utils.helper_methods import load_script_config, get_ip, unpack_launcher, load_config, get_gui_widgets, get_legend_from_graphics_view, find_client, load_script_config, get_gui_widgets_dummy
import time
from pylabnet.scripts.pid import PID


# Static methods

# def generate_widgets():
#     """Static method to return systematically named gui widgets for 4ch wavemeter monitor"""

#     graphs, legends, numbers = [], [], []
#     for i in range(2):
#         graphs.append('graph_widget_' + str(i + 1))
#         legends.append('legend_widget_' + str(i + 1))
#         numbers.append('number_label_' + str(i + 1))
#     for i in range(2, 8):
#         numbers.append('number_label_' + str(i + 1))
#     return graphs, legends, numbers


class CountMonitor:

    # Generate all widget instances for the .ui to use
    # _plot_widgets, _legend_widgets, _number_widgets = generate_widgets()

    def __init__(self, ctr_client_in: nidaqmx_card, ctr_client_out: nidaqmx_card, ui='count_monitor', logger_client=None, server_port=None, combined_channel=False, config=None):
        """ Constructor for CountMonitor script

        :param ctr_client: instance of hardware client for counter
        :param gui_client: (optional) instance of client of desired output GUI
        :param logger_client: (obj) instance of logger client.
        :param server_port: (int) port number of script server
        :combined_channel: (bool) If true, show additional trace with summed counts.
        """

        self._ctr_in = ctr_client_in
        self._ctr_out = ctr_client_out
        self.log = logger_client
        self.combined_channel = combined_channel
        self._bin_width = None
        self._n_bins = None
        self._ch_list = None
        self._plot_list = None  # List of channels to assign to each plot (e.g. [[1,2], [3,4]])
        self._plots_assigned = []  # List of plots on the GUI that have been assigned
        self.data = None
        self.x = None
        self.pid = None
        self.gain = None
        self.output = None



        # Instantiate GUI window
        self.gui = Window(
            gui_template=ui,
            host=get_ip(),
            port=server_port,
            log=self.log
        )

        # Setup stylesheet.
        self.gui.apply_stylesheet()

        num_plots = 2

        # Get all GUI widgets
        self.widgets = get_gui_widgets_dummy(
            self.gui,
            graph_widget=num_plots,
            number_label=3,
            event_button=num_plots,
            legend_widget=num_plots
        )

        # Load config
        self.config = {}
        if config is not None:
            self.config = load_script_config(
                script='monitor_counts',
                config=config,
                logger=self.logger_client
            )

        if not 'name' in self.config:
            self.config.update({'name': f'monitor{np.random.randint(1000)}'})

    def set_hardware(self, ctr_in,  ctr_out):
        """ Sets hardware client for this script

        :param ctr: instance of count monitor hardware client
        """

        # Initialize counter instance
        self._ctr_in = ctr_in
        self._ctr_out = ctr_out


    def set_params(self, bin_width=1e9, n_bins=1e3, ch_list=[1], plot_list=None, locking_point=0, P=0, I=0, D=0, memory=20, gain=1 ):
        """ Sets counter parameters

        :param bin_width: bin width in ps
        :param n_bins: number of bins to display on graph
        :param ch_list: (list) channels to record
        :param plot_list: list of channels to assign to each plot (e.g. [[1,2], [3,4]])
        """

        dt_timestamp = time.time()

        # Save params to internal variables
        self._bin_width = int(bin_width)
        self._n_bins = int(n_bins)
        self._ch_list = ch_list
        self._plot_list = plot_list
        self.data = np.zeros([len(ch_list), self._n_bins])
        self.x = np.ones(self._n_bins) * dt_timestamp
        self.pid = PID(
                p=P,
                i=I,
                d=D,
                memory=memory,
                setpoint=locking_point
            )
        self.gain = gain
        self.output = 0


    def run(self):
        """ Runs the counter from scratch"""

        try:

            # Start the counter with desired parameters
            self._initialize_display()

            # Give time to initialize
            # time.sleep(0.05)
            self._is_running = True

            # Continuously update data until paused
            while self._is_running:
                self._update_output()
                self.gui.force_update()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):
        """ Pauses the counter"""

        self._is_running = False

    def resume(self):
        """ Resumes the counter.

        To be used to resume after the counter has been paused.
        """

        try:
            self._is_running = True

            # Clear counter and resume plotting
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    # Technical methods

    def _initialize_display(self):
        """ Initializes the display (configures all plots) """

        plot_index = 0
        for index in range(len(self.widgets['graph_widget'])):
            # Configure and return legend widgets
            self.widgets['legend_widget'][index] = get_legend_from_graphics_view(
                self.widgets['legend_widget'][index]
            )

        for color, channel in enumerate(self._ch_list):

            # Figure out which plot to assign to
            if self._plot_list is not None:
                for index, channel_set in enumerate(self._plot_list):
                    if channel in channel_set:
                        plot_index = index
                        break

            # If we have not assigned this plot yet, assign it
            # if plot_index not in self._plots_assigned:
            #     self.gui_handler.assign_plot(
            #         plot_widget=self._plot_widgets[plot_index],
            #         plot_label='Counter Monitor {}'.format(plot_index + 1),
            #         legend_widget=self._legend_widgets[plot_index]
            #     )
            #     self._plots_assigned.append(plot_index)

            # Now assign this curve
            # self.gui_handler.assign_curve(
            #     plot_label='Counter Monitor {}'.format(plot_index + 1),
            #     curve_label='Channel {}'.format(channel),
            #     error=True
            # )

            # Create a curve and store the widget in our dictionary
            self.widgets[f'curve_{channel}'] = self.widgets['graph_widget'][plot_index].plot(
                pen=pg.mkPen(color=self.gui.COLOR_LIST[color])
            )
            self.widgets['legend_widget'][plot_index].addItem(
                self.widgets[f'curve_{channel}'],
                ' - ' + f'Channel {channel}'
            )

            # Assign scalar
            # self.gui_handler.assign_label(
            #     label_widget=self._number_widgets[channel - 1],
            #     label_label='Channel {}'.format(channel)
            # )

        # Handle button pressing
        from functools import partial

        for plot_index, clear_button in enumerate(self.widgets['event_button']):
            clear_button.clicked.connect(partial(lambda plot_index: self._clear_plot(plot_index), plot_index=plot_index))


    def _clear_plot(self, plot_index):
        """ Clears the curves on a particular plot

        :param plot_index: (int) index of plot to clear
        """
        dt_timestamp = time.time()

        # Find all curves in this plot
        for index, channel in enumerate(self._plot_list[plot_index]):

            # Set the curve to constant with last point for all entries
            self.data[index] = np.ones(self._n_bins) * self.widgets[f'curve_{channel}'].yData[-1]
            self.x = np.ones(self._n_bins) * dt_timestamp


            self.widgets[f'curve_{channel}'].setData(
                self.x, self.data[index]
            )

    def _update_output(self):
        """ Updates the output to all current values"""

        # Update all active channels + do locking loop
        voltage = np.mean(self._ctr_in.get_ai_voltage('ai0', 10, 10) )
        # voltage_0 = np.mean(self._ctr_in.get_ai_voltage('ai0', 10, 10) )
        # self._ctr_out.set_ao_voltage('ao4', self.output + 0.25)
        # voltage_1 = np.mean(self._ctr_in.get_ai_voltage('ai0', 10, 10) )
        # self._ctr_out.set_ao_voltage('ao4', self.output - 0.25)
        # voltage_2 = np.mean(self._ctr_in.get_ai_voltage('ai0', 10, 10) )

        # if(voltage_1 > voltage_0):
        #     self.output += 0.25
        # elif(voltage_2 > voltage_0):
        #     self.output -= 0.25

        # if(self.output > 9):
        #     self.output -= 6.5
        # elif(self.output < -9):
        #     self.output += 6.5
        # self.output = max( min(self.output, 9), -9)
        # self._ctr_out.set_ao_voltage('ao4', self.output)
        



        # voltage = voltage_0 



        dt_timestamp = time.time()

        # update voltage
        self.x = np.concatenate((self.x[1:], np.array([dt_timestamp])))
        self.data[0] = np.concatenate((self.data[0, 1:], np.array([voltage]) ) )
        # self.data[1] = np.concatenate((self.data[1, 1:], np.array([monitor_signal]) ) )


        # locking part
        self._lock( )
        self._ctr_out.set_ao_voltage('ao4', self.output)

        # update output
        self.data[2] = np.concatenate((self.data[2, 1:], np.array([self.output])) )


        data = [voltage, 0, self.output]

        for index, v in enumerate(data):

            # Figure out which plot to assign to
            channel = self._ch_list[index]

            v = np.array([v])

            self.widgets[f'curve_{channel}'].setData(self.x-self.x[0], self.data[index])
            if(index==0):
                self.widgets[f'number_label'][channel - 1].setText(str(  format(self.data[index][-1], ".8f")   )) 
            else:
                self.widgets[f'number_label'][channel - 1].setText(str(  format(self.data[index][-1], ".4f")   )) 




    def _lock(self):
        # pid
        self.pid.set_pv(pv=self.data[0,:-self.pid.memory])
        self.pid.set_cv()

        # set output
        self.output += self.pid.cv * self.gain 

        # protection
        # self.output = min(self.output, 9.5)
        # self.output = max(self.output, -9.5ssssssss)
        if(self.output > 9.5): self.output -=2
        if( self.output < -9.5): self.output += 2.
        # if( self.output < -9.5): self.output += 2.
        
        
        # scan
        # dir = 1 if(self.data[2, -1] - self.data[2, -2] >= 0) else -1
        # if( (self.output >= 3.5 and dir==1) or (self.output <= -3.5 and dir==-1) ):
        #     dir *= -0.5
        # self.output += 1 * dir

        return



def launch(**kwargs):
    """ Launches the count monitor script """

    # logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(
        'monitor_counts',
        kwargs['config'],
        logger
    )

    # Instantiate CountMonitor
    try:
        monitor = CountMonitor(
            ctr_client_in=find_client(
                clients,
                config,
                client_type="nidaqmx",
                client_config="daq_ai",
                logger=logger
            ),
            ctr_client_out=find_client(
                clients,
                config,
                client_type="nidaqmx",
                client_config="daq_ao",
                logger=logger
            ),
            logger_client=logger,
            server_port=kwargs['server_port'],
            combined_channel=False
        )
    except KeyError:
        print('Please make sure the module names for required servers and GUIS are correct.')
        time.sleep(15)
        raise


    # Set parameters
    monitor.set_params(**config['params'])

    # Run
    monitor.run()
