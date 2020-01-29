from pylabnet.gui.pyqt import external_gui
from pylabnet.utils.decorators.gui_decorators import gui_connect_check, protected_widget_change
import pickle



class GUIHandler():
    """Generic Parent class for all GUI handlers"""

    def __init__(self,  client=None):
        """
        Instantiates generic GUI configurator

        :param client: (obj)
            instance of hardware client
        """

        self.is_running = False  # Flag which lets us know if WlmMonitor is running
        self.is_paused = False  # Flag which tells us we have simply paused WlmMonitor operation
        self._gui_connected = False  # Flag which alerts if a GUI client has been connected successfully
        self._gui_reconnect = False  # Flag which tells us to try reconnecting to the GUI client

        self.gui = None
        self.client = client

    def assign_gui(self, gui_client):
        """
        Assigns a GUI client to the GUI handler

        :param client:
            (obj) instance of GUI client
        """

        self.gui = gui_client

    def assign_client(self, client):
        """
        Assigns the hardware client to the GUI handler

        :param client:
            (obj) instance of hardware client
        """

        self.client = client

    # Functions called on gui client with corresponding error_handling decorator
    @protected_widget_change
    @gui_connect_check
    def assign_plot(self, plot_widget, plot_label, legend_widget):
        return self.gui._service.exposed_assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    @protected_widget_change
    @gui_connect_check
    def clear_plot(self, plot_widget):
        return self.gui._service.exposed_clear_plot(
            plot_widget=plot_widget
        )

    @protected_widget_change
    @gui_connect_check
    def assign_curve(self, plot_label, curve_label):
        return self.gui._service.exposed_assign_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    @protected_widget_change
    @gui_connect_check
    def remove_curve(self, plot_label, curve_label):
        return self.gui._service.exposed_remove_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    @protected_widget_change
    @gui_connect_check
    def assign_scalar(self, scalar_widget, scalar_label):
        self.gui._service.exposed_assign_scalar(
            scalar_widget=scalar_widget,
            scalar_label=scalar_label
        )

    @protected_widget_change
    @gui_connect_check
    def assign_label(self, label_widget, label_label):
        return self.gui._service.exposed_assign_label(
            label_widget=label_widget,
            label_label=label_label
        )

    @protected_widget_change
    @gui_connect_check
    def assign_event_button(self, event_widget, event_label):
        return self.gui._service.exposed_assign_event_button(
            event_widget=event_widget,
            event_label=event_label
        )

    @protected_widget_change
    @gui_connect_check
    def set_curve_data(self, data, plot_label, curve_label, error=None):
        data_pickle = pickle.dumps(data)
        error_pickle = pickle.dumps(error)
        return self.gui._service.exposed_set_curve_data(
            data_pickle=data_pickle,
            plot_label=plot_label,
            curve_label=curve_label,
            error_pickle=error_pickle
        )

    @protected_widget_change
    @gui_connect_check
    def set_scalar(self, value, scalar_label):
        value_pickle = pickle.dumps(value)
        return self.gui._service.exposed_set_scalar(
            value_pickle=value_pickle,
            scalar_label=scalar_label
        )

    @protected_widget_change
    @gui_connect_check
    def get_scalar(self, scalar_label):
        return pickle.loads(self.gui._service.exposed_get_scalar(scalar_label))

    @protected_widget_change
    @gui_connect_check
    def activate_scalar(self, scalar_label):
        return self.gui._service.exposed_activate_scalar(scalar_label)

    @protected_widget_change
    @gui_connect_check
    def deactivate_scalar(self, scalar_label):
        return self.gui._service.exposed_deactivate_scalar(scalar_label)

    @protected_widget_change
    @gui_connect_check
    def set_label(self, text, label_label):
        return self.gui._service.exposed_set_label(
            text=text,
            label_label=label_label
        )

    @protected_widget_change
    @gui_connect_check
    def was_button_pressed(self, event_label):
        return self.gui._service.exposed_was_button_pressed(event_label)







