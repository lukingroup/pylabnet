from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import unpack_launcher, generate_widgets


class Controller:
    """ A script class for controlling MCS2 positioners + interfacing with GUI"""

    NUM_CHANNELS = 9
    WIDGET_DICT = dict(
        step_left=NUM_CHANNELS, step_right=NUM_CHANNELS, walk_left=NUM_CHANNELS,
        walk_right=NUM_CHANNELS, n_steps=NUM_CHANNELS, is_moving=NUM_CHANNELS,
        amplitude=NUM_CHANNELS, frequency=NUM_CHANNELS, velocity=NUM_CHANNELS, voltage=NUM_CHANNELS
    )

    def __init__(self, nanopos_client, gui_client, log_client=None):
        """ Instantiates the controller

        :param nanopos_client: (pylabnet.network.client_server.smaract_mcs2.Client)
        :param gui_client: (pylabnet.network.client_server.external_gui.Client)
        :param log_client: (pylabnet.utils.logging.logger.LogClient)
        """

        self.pos = nanopos_client
        self.log = LogHandler(logger=log_client)
        self.gui = GUIHandler(gui_client=gui_client, logger_client=self.log)

        # Unpack all widgets
        (self.step_left, self.step_right, self.walk_left, self.walk_right,
         self.n_steps, self.is_moving, self.amplitude, self.frequency,
         self.velocity, self. voltage) = generate_widgets(self.WIDGET_DICT)

    def initialize_gui(self):
        """ Initializes the GUI (assigns channels)"""

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            self._initialize_channel(channel_index)

    def run(self):
        """ Runs the Positioner control (takes any necessary action) """

        # Iterate through channels
        for channel_index in range(self.NUM_CHANNELS):

            # Update status of positioner
            pass


    # Technical methods

    def _initialize_channel(self, index):
        """ Initializes GUI for a given channel"""

        # Assign all numbers & boolean indicators
        self.gui.assign_scalar(scalar_widget=self.n_steps[index], scalar_label=self.n_steps[index])
        self.gui.assign_scalar(
            scalar_widget=self.amplitude[index], scalar_label=self.amplitude[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.frequency[index], scalar_label=self.frequency[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.velocity[index], scalar_label=self.velocity[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.voltage[index], scalar_label=self.voltage[index]
        )
        self.gui.assign_scalar(
            scalar_widget=self.is_moving[index], scalar_label=self.is_moving[index]
        )

        # Assign pushbuttons
        self.gui.assign_event_button(
            event_widget=self.step_left[index], event_label=self.step_left[index]
        )
        self.gui.assign_event_button(
            event_widget=self.step_right[index], event_label=self.step_right[index]
        )
        self.gui.assign_event_button(
            event_widget=self.walk_left[index], event_label=self.walk_left[index]
        )
        self.gui.assign_event_button(
            event_widget=self.walk_left[index], event_label=self.walk_left[index]
        )


def launch(**kwargs):
    """ Launches the full nanopositioner control + GUI script """

    # Unpack and assign parameters
    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)
    nanopos_client = clients['smaract_mcs2']
    gui_client = guis['positioner_control']

    # Instantiate controller
    control = Controller(nanopos_client, gui_client, logger)

    # Initialize all GUI channels
    control.initialize_gui()

    while True:

        if not control.gui.is_paused:
            control.run()
