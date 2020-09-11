from pylabnet.network.client_server import toptica_dl_pro, external_gui
from pylabnet.scripts.lasers import wlm_monitor
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher


class Controller:
    """ Class for controlling Toptica scan and laser properties """

    def __init__(self, dlc: toptica_dl_pro.Client, 
        gui: external_gui.Client, logger=None):
        """ Initializes toptica specific parameters 
        
        :param dlc: DLC client for the Toptica laser
        :param gui: GUI client for Toptica params
        """

        self.log = LogHandler(logger)

        # Assign GUI parameters
        self.gui = gui
        self._assign_GUI()
        
        self.dlc = dlc
        self.current_sp = self.dlc.current_sp()
        self.temp_sp = self.dlc.temp_sp()
        self.offset = 65
        self.amplitude = 100
        self.scan = False

        self._setup_GUI()

    def run(self):
        """ Runs an iteration of checks for updates and implements """

        # First check for parameter updates
        if self.gui.was_button_pressed('update_temp'):
            temp = self.gui.get_scalar('temperature')
            self.dlc.set_temp(temp)
            self.log.info(f'Toptica DL temperature set to {temp}')
        if self.gui.was_button_pressed('update_current'):
            current = self.gui.get_scalar('current')
            self.dlc.set_current(current)
            self.log.info(f'Toptica DL current set to {current}')
        
        # Now handle a scan event
        if self.gui.get_scalar('scan') != self.scan:

            # If we were previously scanning, terminate the scan
            if self.scan:
                self.dlc.stop_scan()
                self.log.info(f'Toptica DL scan stopped')

            # Otherwise, configure and start the scan
            else:
                offset = self.gui.get_scalar('offset')
                amplitude = self.gui.get_scalar('amplitude')
                self.dlc.configure_scan(
                    offset=offset,
                    amplitude=amplitude
                )
                self.dlc.start_scan()
                self.log.info('Toptica DL Scan initiated '
                              f'with offset: {offset}, '
                              f'amplitude: {amplitude}')

    def _assign_GUI(self):
        """ Assigns widgets in GUI """

        self.gui.assign_scalar('temperature', 'temperature')
        self.gui.assign_scalar('current', 'current')
        self.gui.assign_scalar('offset', 'offset')
        self.gui.assign_scalar('amplitude', 'amplitude')
        self.gui.assign_scalar('scan', 'scan')
        self.gui.assign_event_button('update_temp', 'update_temp')
        self.gui.assign_event_button('update_current', 'update_current')

    def _setup_GUI(self):
        """ Sets values to current parameters """

        self.gui.activate_scalar('temperature')
        self.gui.set_scalar(self.temp_sp, 'temperature')
        self.gui.deactivate_scalar('temperature')

        self.gui.activate_scalar('current')
        self.gui.set_scalar(self.current_sp, 'current')
        self.gui.deactivate_scalar('current')

        self.gui.activate_scalar('scan')
        self.gui.set_scalar(False, 'scan')
        self.gui.deactivate_scalar('scan')


def launch(**kwargs):

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    dlc_client = clients['toptica_dlc_pro']
    gui_client = guis['toptica_control']

    # Instantiate Monitor script
    toptica_controller = Controller(dlc_client, gui_client, logger=logger)

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        toptica_controller.run()
