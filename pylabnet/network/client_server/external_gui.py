import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.network.core.generic_server import GenericServer


class Service(ServiceBase):

    def exposed_assign_plot(self, plot_widget, plot_label, legend_widget):
        return self._module.assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    def exposed_clear_plot(self, plot_widget):
        return self._module.clear_plot(
            plot_widget=plot_widget
        )

    def exposed_assign_curve(self, plot_label, curve_label, error=False):
        return self._module.assign_curve(
            plot_label=plot_label,
            curve_label=curve_label,
            error=error
        )

    def exposed_remove_curve(self, plot_label, curve_label):
        self._module.remove_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    def exposed_assign_scalar(self, scalar_widget, scalar_label):
        return self._module.assign_scalar(
            scalar_widget=scalar_widget,
            scalar_label=scalar_label
        )

    def exposed_assign_label(self, label_widget, label_label):
        return self._module.assign_label(
            label_widget=label_widget,
            label_label=label_label
        )

    def exposed_assign_event_button(self, event_widget, event_label):
        return self._module.assign_event_button(
            event_widget=event_widget,
            event_label=event_label,

        )

    def exposed_assign_container(self, container_widget, container_label):
        return self._module.assign_container(self, container_widget, container_label)
    
    def exposed_set_curve_data(self, data_pickle, plot_label, curve_label, error_pickle=None):
        data = pickle.loads(data_pickle)
        error = pickle.loads(error_pickle)
        return self._module.set_curve_data(
            data=data,
            plot_label=plot_label,
            curve_label=curve_label,
            error=error
        )

    def exposed_set_scalar(self, value_pickle, scalar_label):
        value = pickle.loads(value_pickle)
        return self._module.set_scalar(
            value=value,
            scalar_label=scalar_label
        )

    def exposed_get_scalar(self, scalar_label):
        return pickle.dumps(self._module.get_scalar(scalar_label))

    def exposed_activate_scalar(self, scalar_label):
        return self._module.activate_scalar(scalar_label)

    def exposed_deactivate_scalar(self, scalar_label):
        return self._module.deactivate_scalar(scalar_label)

    def exposed_set_label(self, text, label_label):
        return self._module.set_label(
            text=text,
            label_label=label_label
        )

    def exposed_get_text(self, label_label):
        return pickle.dumps(self._module.get_text(label_label))
    
    def exposed_was_button_pressed(self, event_label):
        return self._module.was_button_pressed(event_label)

    def exposed_change_button_background_color(self, event_label, color):
        return self._module.change_button_background_color(self, event_label, color)

    def exposed_get_container_info(self, container_label):
        return pickle.dumps(self._module.get_container_info(container_label))


class Client(ClientBase):

    def assign_plot(self, plot_widget, plot_label, legend_widget):
        return self._service.exposed_assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    def clear_plot(self, plot_widget):
        return self._service.exposed_clear_plot(
            plot_widget=plot_widget
        )

    def assign_curve(self, plot_label, curve_label, error=False):
        return self._service.exposed_assign_curve(
            plot_label=plot_label,
            curve_label=curve_label,
            error=error
        )

    def remove_curve(self, plot_label, curve_label):
        return self._service.exposed_remove_curve(
            plot_label=plot_label,
            curve_label=curve_label
        )

    def assign_scalar(self, scalar_widget, scalar_label):
        self._service.exposed_assign_scalar(
            scalar_widget=scalar_widget,
            scalar_label=scalar_label
        )

    def assign_label(self, label_widget, label_label):
        return self._service.exposed_assign_label(
            label_widget=label_widget,
            label_label=label_label
        )

    def assign_event_button(self, event_widget, event_label):
        return self._service.exposed_assign_event_button(
            event_widget=event_widget,
            event_label=event_label,
        )

    def assign_container(self, container_widget, container_label):
        return self._service.exposed_assign_container(container_widget, container_label)
    
    def set_curve_data(self, data, plot_label, curve_label, error=None):
        data_pickle = pickle.dumps(data)
        error_pickle = pickle.dumps(error)
        return self._service.exposed_set_curve_data(
            data_pickle=data_pickle,
            plot_label=plot_label,
            curve_label=curve_label,
            error_pickle=error_pickle
        )

    def set_scalar(self, value, scalar_label):
        value_pickle = pickle.dumps(value)
        return self._service.exposed_set_scalar(
            value_pickle=value_pickle,
            scalar_label=scalar_label
        )

    def get_scalar(self, scalar_label):
        return pickle.loads(self._service.exposed_get_scalar(scalar_label))

    def activate_scalar(self, scalar_label):
        return self._service.exposed_activate_scalar(scalar_label)

    def deactivate_scalar(self, scalar_label):
        return self._service.exposed_deactivate_scalar(scalar_label)

    def set_label(self, text, label_label):
        return self._service.exposed_set_label(
            text=text,
            label_label=label_label
        )

    def get_text(self, label_label):
        return pickle.loads(self._service.exposed_get_text(label_label))
    
    def was_button_pressed(self, event_label):
        return self._service.exposed_was_button_pressed(event_label)

    def change_button_background_color(self, event_label, color):
        return self._service.exposed_change_button_background_color(self, event_label, color)

    def get_container_info(self, container_label):
        return pickle.loads(self._service.exposed_get_container_info(container_label))

