from pylabnet.utils.decorators.gui_decorators import handle_gui_errors
import pickle


class GUIHandler():
    """Generic GUI handler class providing an error-tolerant GUI client - script Interface.

    Member variables of this class keep track of connection parameters
    (is_running, is_connected, etc.), and global error handling is performed
    in the @handle_gui_errors decorator, which is applied to all calls
    from the GUIHandler to a GUI client.

    :gui_client: (object)
        GUI client to be called.
    :logger_client: (object)
        Logger client used for error logging in  @handle_gui_errors
        decorator.
    """

    def __init__(self,  gui_client=None, logger_client=None):

        self.is_running = False  # Flag which lets us know if WlmMonitor is running
        self.is_paused = False  # Flag which tells us we have simply paused WlmMonitor operation
        self.gui_connected = False  # Flag which alerts if a GUI client has been connected successfully
        self.gui_reconnect = False  # Flag which tells us to try reconnecting to the GUI client

        self.gui_client = gui_client
        self.logger_client = logger_client

    def assign_gui(self, gui_client):
        """Assigns a GUI client to the GUI handler

        :param client:
            (obj) instance of GUI client
        """

        self.gui = gui_client

    def pause(self):
        """Pauses the wavemeter monitor"""
        self.is_running = False
        self.is_paused = True

    def resume(self):
        """Resumes the wavemeter monitor when paused"""
        self.is_paused = False

    def reconnect_gui(self):
        """ Reconnects to the GUI

        Should be called if the GUI connection has been lost, once a new GUI client with the same access parameters has
        been reinstantiated
        """
        self.gui_reconnect = True

    # Functions called on gui client with corresponding error_handling decorator
    @handle_gui_errors
    def assign_plot(self, plot_widget, plot_label, legend_widget):
        return self.gui_client.assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    @handle_gui_errors
    def clear_plot(self, plot_widget):
        return self.gui_client.clear_plot(
            plot_widget=plot_widget
        )

    @handle_gui_errors
    def assign_curve(self, plot_label, curve_label, error=False):
        return self.gui_client.assign_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    @handle_gui_errors
    def remove_curve(self, plot_label, curve_label):
        return self.gui_client.remove_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    @handle_gui_errors
    def assign_scalar(self, scalar_widget, scalar_label):
        self.gui_client.assign_scalar(
            scalar_widget=scalar_widget,
            scalar_label=scalar_label
        )

    @handle_gui_errors
    def assign_label(self, label_widget, label_label):
        return self.gui_client.assign_label(
            label_widget=label_widget,
            label_label=label_label
        )

    @handle_gui_errors
    def assign_event_button(self, event_widget, event_label):
        return self.gui_client.assign_event_button(
            event_widget=event_widget,
            event_label=event_label,
        )

    @handle_gui_errors
    def assign_event_button_event(self, event_label, function):
        return self.gui_client.assign_event_button_event(
            event_label=event_label,
            function=function,
        )

    @handle_gui_errors
    def set_curve_data(self, data, plot_label, curve_label, error=None):
        return self.gui_client.set_curve_data(
            data=data,
            plot_label=plot_label,
            curve_label=curve_label,
            error=error
        )

    @handle_gui_errors
    def set_scalar(self, value, scalar_label):
        return self.gui_client.set_scalar(
            value=value,
            scalar_label=scalar_label
        )

    @handle_gui_errors
    def get_scalar(self, scalar_label):
        return self.gui_client.get_scalar(scalar_label)

    @handle_gui_errors
    def activate_scalar(self, scalar_label):
        return self.gui_client.activate_scalar(scalar_label)

    @handle_gui_errors
    def deactivate_scalar(self, scalar_label):
        return self.gui_client.deactivate_scalar(scalar_label)

    @handle_gui_errors
    def set_label(self, text, label_label):
        return self.gui_client.set_label(
            text=text,
            label_label=label_label
        )

    @handle_gui_errors
    def was_button_pressed(self, event_label):
        return self.gui_client.was_button_pressed(event_label)
