from pylabnet.network.client_server import toptica_dl_pro, external_gui
from pylabnet.scripts.lasers import wlm_monitor
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, get_gui_widgets, find_client, load_script_config
from pylabnet.gui.pyqt.external_gui import Window

import socket
import time
import numpy as np


class Controller:
    """ Class for controlling Toptica scan and laser properties """

    def __init__(self, dlc: toptica_dl_pro.Client,
        gui='toptica_control', logger=None, port=None):
        """ Initializes toptica specific parameters

        :param dlc: DLC client for the Toptica laser
        :param gui: .ui file to use
        :param logger: LogClient for logging purposes
        :param port: port number of script server
        """

        self.log = LogHandler(logger)

        # Setup GUI
        self.gui = Window(
            gui_template=gui,
            host=socket.gethostbyname(socket.gethostname()),
            port=port
        )
        self.widgets = get_gui_widgets(
            gui=self.gui,
            on_off=2,
            temperature=2,
            temperature_actual=2,
            current=2,
            current_actual=2,
            offset=2,
            amplitude=2,
            frequency=2,
            scan=2,
            update_temp=2,
            update_current=2,
            update_params=1
        )

        self.dlc = dlc
        self.offset = 65
        self.amplitude = 100
        self.scan = [False, False]
        self.emission = [False, False]


        # Setup stylesheet.
        self.gui.apply_stylesheet()

        self._setup_GUI()

    def run(self, check_vals=False):
        """ Runs an iteration of checks for updates and implements

        :param check_vals: (bool) whether or not to check the values of current and temp
        """

        # Update actual current and temperature
        # self.gui.activate_scalar('temperature_actual')
        # self.gui.set_scalar(self.dlc.temp_act(), 'temperature_actual')
        # self.gui.deactivate_scalar('temperature_actual')

        # self.gui.activate_scalar('current_actual')
        # self.gui.set_scalar(self.dlc.current_act(), 'current_actual')
        # self.gui.deactivate_scalar('current_actual')


        # Check for on/off updates
        for i in range(2):
            if self.widgets['on_off'][i].isChecked() != self.emission[i]:

                # If laser was already on, turn off
                if self.emission[i]:
                    self.dlc.turn_off(i+1)
                    self.emission[i] = False
                    self.log.info(f'Toptica DL {i+1} turned off')

                # Otherwise turn on
                else:
                    self.dlc.turn_on(i+1)
                    self.emission[i] = True
                    self.log.info(f'Toptica DL {i+1} turned on')

        # Now handle a scan event
        for i in range(2):
            if self.widgets['scan'][i].isChecked() != self.scan[i]:

                # If we were previously scanning, terminate the scan
                if self.scan[i]:
                    self.dlc.stop_scan(i+1)
                    self.scan[i] = False
                    self.log.info(f'Toptica DL {i+1} scan stopped')

                # Otherwise, configure and start the scan
                else:
                    offset = self.widgets['offset'][i].value()
                    amplitude = self.widgets['amplitude'][i].value()
                    frequency = self.widgets['frequency'][i].value()
                    self.dlc.configure_scan(
                        offset=offset,
                        amplitude=amplitude,
                        frequency=frequency,
                        laser_num=i+1
                    )
                    self.dlc.start_scan(i+1)
                    self.scan[i] = True
                    self.log.info(f'Toptica DL Scan {i+1} initiated '
                                f'with offset: {offset}, '
                                f'amplitude: {amplitude}, '
                              f'frequency: {frequency}')

        # Handle value checking
        if self.widgets['update_params'].isChecked():

            for i in range(2):
                self.widgets['temperature_actual'][i].setDisabled(False)
                self.widgets['current_actual'][i].setDisabled(False)

            if check_vals:
                try:
                    temp_1 = self.dlc.temp_act(1)
                    if temp_1 < 50:
                        self.widgets['temperature_actual'][0].setValue(
                            temp_1
                        )
                    time.sleep(0.1)
                    self.widgets['current_actual'][0].setValue(
                        self.dlc.current_act(1)
                    )
                    temp_2 = self.dlc.temp_act(2)
                    if temp_2 < 50:
                        self.widgets['temperature_actual'][1].setValue(
                            temp_2
                        )
                    time.sleep(0.1)
                    self.widgets['current_actual'][1].setValue(
                        self.dlc.current_act(2)
                    )
                except ValueError:
                    pass
        else:
            for i in range(2):
                self.widgets['temperature_actual'][i].setDisabled(True)
                self.widgets['current_actual'][i].setDisabled(True)



        self.gui.force_update()

    def _setup_GUI(self):
        """ Sets values to current parameters """

        # Check if laser is on and update

        for i in range(2):
            self.emission[i] = self.dlc.is_laser_on(i+1)
            self.widgets['on_off'][i].setChecked(self.emission[i])
            time.sleep(0.1)

        # Get temperature setpoint and actual temperature
        temp_sp_1=100
        while temp_sp_1 > 50:
            temp_sp_1 = self.dlc.temp_sp(1)
            temp_sp_2 = self.dlc.temp_sp(2)
            time.sleep(0.1)

        self.widgets['temperature'][0].setValue(temp_sp_1)
        self.widgets['temperature'][1].setValue(temp_sp_2)

        temp_act_1=100
        while temp_act_1 > 50:
            temp_act_1 = self.dlc.temp_act(1)
            temp_act_2 = self.dlc.temp_act(2)
            time.sleep(0.1)
        self.widgets['temperature_actual'][0].setValue(temp_act_1)
        self.widgets['temperature_actual'][1].setValue(temp_act_2)

        # Get current setpoint and actual current
        self.widgets['current'][0].setValue(self.dlc.current_sp(1))
        time.sleep(0.1)
        self.widgets['current'][1].setValue(self.dlc.current_sp(2))
        time.sleep(0.1)
        self.widgets['current_actual'][0].setValue(self.dlc.current_act(1))
        time.sleep(0.1)
        self.widgets['current_actual'][1].setValue(self.dlc.current_act(2))
        time.sleep(0.1)


        # Assign button pressing
        self.widgets['update_temp'][0].clicked.connect(lambda: self._set_temperature(1))
        self.widgets['update_temp'][1].clicked.connect(lambda: self._set_temperature(2))
        self.widgets['update_current'][0].clicked.connect(lambda: self._set_current(1))
        self.widgets['update_current'][1].clicked.connect(lambda: self._set_current(2))

    def _set_temperature(self, laser_num):
        """ Sets the temperature to the setpoint value in the GUI """

        temperature = self.widgets['temperature'][laser_num-1].value()
        self.dlc.set_temp(temperature, laser_num)
        self.log.info(f'Set Toptica {laser_num} temperature setpoint to {temperature}')

    def _set_current(self, laser_num):
        """ Sets the current to the setpoint value in the GUI """

        current = self.widgets['current'][laser_num-1].value()
        self.dlc.set_current(current, laser_num)
        self.log.info(f'Set Toptica {laser_num} current setpoint to {current}')


def launch(**kwargs):

    logger = kwargs['logger']
    clients = kwargs['clients']
    config = load_script_config(script='toptica_control',
                                config=kwargs['config'],
                                logger=logger)


    dlc_client = find_client(clients=clients, settings=config, client_type='toptica_dlc_pro')

    # Instantiate Monitor script
    toptica_controller = Controller(dlc_client, logger=logger, port=kwargs['server_port'])

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    start_time = time.time()
    check_interval = 1
    while True:

        if time.time()-start_time < check_interval:
            toptica_controller.run()
        else:
            toptica_controller.run(check_vals=True)
            start_time = time.time()
