from pylabnet.network.client_server import toptica_dl_pro, external_gui
from pylabnet.scripts.lasers import wlm_monitor
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import get_ip, unpack_launcher, get_gui_widgets, find_client, load_script_config
from pylabnet.gui.pyqt.external_gui import Window

import time
import numpy as np


class Controller:
    """ Class for controlling Toptica scan and laser properties """

    def __init__(self, dlc: toptica_dl_pro.Client,
                 gui='toptica_control', logger=None, port=None, config=None):
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
            host=get_ip(),
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
        self.config = config
        self.num_lasers = int(self.config["num_lasers"])
        self.scan = [False] * self.num_lasers
        self.emission = [False] * self.num_lasers

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
        for i in range(self.num_lasers):
            if self.widgets['on_off'][i].isChecked() != self.emission[i]:

                # If laser was already on, turn off
                if self.emission[i]:
                    self.dlc.turn_off(i + 1)
                    self.emission[i] = False
                    self.log.info(f'Toptica DL {i+1} turned off')

                # Otherwise turn on
                else:
                    self.dlc.turn_on(i + 1)
                    self.emission[i] = True
                    self.log.info(f'Toptica DL {i+1} turned on')

        # Now handle a scan event
        for i in range(self.num_lasers):
            if self.widgets['scan'][i].isChecked() != self.scan[i]:

                # If we were previously scanning, terminate the scan
                if self.scan[i]:
                    self.dlc.stop_scan(i + 1)
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
                        laser_num=i + 1
                    )
                    self.dlc.start_scan(i + 1)
                    self.scan[i] = True
                    self.log.info(f'Toptica DL Scan {i+1} initiated '
                                  f'with offset: {offset}, '
                                  f'amplitude: {amplitude}, '
                                  f'frequency: {frequency}')

        # Handle value checking
        if self.widgets['update_params'].isChecked():

            for i in range(self.num_lasers):
                self.widgets['temperature_actual'][i].setDisabled(False)
                self.widgets['current_actual'][i].setDisabled(False)

            if check_vals:
                for i in range(self.num_lasers):
                    try:
                        temp = self.dlc.temp_act(i + 1)
                        if temp < 50:
                            self.widgets['temperature_actual'][i].setValue(temp)
                        time.sleep(0.1)
                        self.widgets['current_actual'][i].setValue(self.dlc.current_act(i + 1))
                    except ValueError:
                        pass
        else:
            for i in range(self.num_lasers):
                self.widgets['temperature_actual'][i].setDisabled(True)
                self.widgets['current_actual'][i].setDisabled(True)

        self.gui.force_update()

    def _setup_GUI(self):
        """ Sets values to current parameters """

        # Check if laser is on and update

        for i in range(self.num_lasers):
            self.emission[i] = self.dlc.is_laser_on(i + 1)
            self.widgets['on_off'][i].setChecked(self.emission[i])
            time.sleep(0.1)

        # Get temperature setpoint and actual temperature
        temp_sp_arr = [100] * self.num_lasers
        while temp_sp_arr[0] > 50:
            for i in range(self.num_lasers):
                temp_sp_arr[i] = self.dlc.temp_sp(i + 1)
            time.sleep(0.1)

        for i in range(self.num_lasers):
            self.widgets['temperature'][i].setValue(temp_sp_arr[i])

        temp_act_arr = [100] * self.num_lasers
        while temp_act_arr[0] > 50:
            for i in range(self.num_lasers):
                temp_act_arr[i] = self.dlc.temp_act(i + 1)
            time.sleep(0.1)

        for i in range(self.num_lasers):
            self.widgets['temperature_actual'][i].setValue(temp_act_arr[i])

        # Get current setpoint and actual current
        for i in range(self.num_lasers):
            self.widgets['current'][i].setValue(self.dlc.current_sp(i + 1))
            time.sleep(0.1)
            self.widgets['current_actual'][i].setValue(self.dlc.current_act(i + 1))
            time.sleep(0.1)

        # Assign button pressing
        for i in range(self.num_lasers):
            self.widgets['update_temp'][i].clicked.connect(lambda: self._set_temperature(i + 1))
            self.widgets['update_current'][i].clicked.connect(lambda: self._set_current(i + 1))

    def _set_temperature(self, laser_num):
        """ Sets the temperature to the setpoint value in the GUI """

        temperature = self.widgets['temperature'][laser_num - 1].value()
        self.dlc.set_temp(temperature, laser_num)
        self.log.info(f'Set Toptica {laser_num} temperature setpoint to {temperature}')

    def _set_current(self, laser_num):
        """ Sets the current to the setpoint value in the GUI """

        current = self.widgets['current'][laser_num - 1].value()
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
    toptica_controller = Controller(dlc_client, logger=logger, port=kwargs['server_port'],
                                    config=config)

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    start_time = time.time()
    check_interval = 1
    while True:

        if time.time() - start_time < check_interval:
            toptica_controller.run()
        else:
            toptica_controller.run(check_vals=True)
            start_time = time.time()
