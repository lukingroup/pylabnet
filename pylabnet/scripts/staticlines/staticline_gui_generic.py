from pylabnet.gui.pyqt.gui_handler import GUIHandler
from pylabnet.utils.helper_methods import unpack_launcher
import pylabnet.hardware.staticline.staticline as staticline
from pylabnet.hardware.staticline.staticline_devices import AbstractDevice

import time


class StaticLineGUIGeneric():
    """Generic Static Line GUI

    :gui_client: (object)
        GUI client to be called.
    :logger_client: (object)
        Logger client used for error logging in  @handle_gui_errors
        decorator.
    :staticline: (object)
        Instance of staticline.Driver
    """

    def __init__(
        self,
        gui_client,
        staticline_client,
        logger_client
    ):

        # Instantiate gui handler
        self.gui_handler = GUIHandler(gui_client, logger_client)

        # TODO: Make it support >1 device/GUI block - need to find a way to autospecify hardware_handler 
        # TODO: Use config files - prob pass configs to Driver() then to hardware_handler()
        # Both TBD after we decide how the GUI is generated and accessed.
        self.staticline = staticline.Driver(
            name='Laser Green',
            logger=logger_client,
            hardware_client=staticline_client,
            hardware_handler=AbstractDevice,
            ao_output='ao2',
            down_voltage=0,
            up_voltage=3.3,
        )

    def initialize_button(
        self,
        button_widget='button_label',
        button_widget_label='button_label_label',
        button_up_widget='up_button',
        button_up_widget_label='up_button_label',
        button_down_widget='down_button',
        button_down_widget_label='down_button_label',

    ):
        """Initialize label to staticline name, assignes labels."""

        label_widgets = [
            button_widget,
        ]

        label_labels = [
            button_widget_label,

        ]

        button_widgets = [
            button_up_widget,
            button_down_widget,
        ]

        button_labels = [
            button_up_widget_label,
            button_down_widget_label,
        ]

        # Assign label labels
        for widget, label in zip(label_widgets, label_labels):
            self.gui_handler.assign_label(widget, label)

        # Assign buttons
        for widget, label in zip(button_widgets, button_labels):
            self.gui_handler.assign_event_button(widget, label)

        # Retrieve staticline names
        staticline_name = self.staticline.get_name()

        # Set value of label staticline names.
        self.gui_handler.set_label(staticline_name, button_widget_label)

        # Store label name
        self.button_up_widget_label = button_up_widget_label
        self.button_down_widget_label = button_down_widget_label

    def check_buttons(self):
        """ Checks state of buttons and sets shutter accordingly"""
        if self.gui_handler.was_button_pressed(event_label=self.button_up_widget_label):
            self.staticline.up()
        elif self.gui_handler.was_button_pressed(event_label=self.button_down_widget_label):
            self.staticline.down()

    def run(self):

        # Initialize button
        self.initialize_button()

        # Mark running flag
        self.gui_handler.is_running = True
        while self.gui_handler.is_running and self.gui_handler.gui_connected:
            self.check_buttons()
            time.sleep(0.02)


def launch(**kwargs):
    """Launches the script."""

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    # Instantiate StaticLineGUIGeneric
    try:
        staticline_gui = StaticLineGUIGeneric(
            staticline_client=clients['abstract'],  # TODO: Support multiple devices
            gui_client=guis['staticline_generic'],  # TODO: Remove this in future.
            logger_client=logger
        )
    except KeyError:
        logger.error('Please make sure the module names for required servers and GUIS are correct.')

    # Run
    staticline_gui.run()
