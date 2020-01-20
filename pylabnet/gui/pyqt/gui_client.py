from pylabnet.gui.pyqt.external_gui import Client
import numpy as np
import time

gui_client = Client(host='localhost', port=9)
gui_client.connect()

# x_axis = np.arange(1000)
# y_axis = np.sin(x_axis*2*np.pi/1000)
# 
# for i in np.linspace(1000,2000,1000):
#     y_axis = np.append(y_axis[1:], np.sin(i*2*np.pi/1000))
#     gui_client.set_data(y_axis)
#     gui_client.update_output()
# 
# gui_client.load_gui()

# Build list of widgets internal to .gui (script specific)
graph_widgets = []
legend_widgets = []
number_widgets = []
bool_widgets = []
for i in range(4):
    graph_widgets.append('graph_widget_'+str(i+1))
    legend_widgets.append('legend_widget_'+str(i+1))
    bool_widgets.append('boolean_widget_'+str(i+1))
    number_widgets.append('number_widget_'+str(i+1))
for i in range(4, 8):
    number_widgets.append('number_widget_'+str(i+1))

# Define our plot, curve, and scalar names
plot_1 = 'Velocity monitor'
p1_curve_1 = 'Velocity frequency'
p1_curve_2 = 'Velocity setpoint'
plot_2 = 'TiSa monitor'
p2_curve_1 = 'TiSa frequency'
freq_1 = 'Velocity frequency'
sp_1 = 'Velocity setpoint'
freq_2 = 'TiSa frequency'
lock_1 = 'Velocity lock'

# Define mapping between key names and widget names
plots = {
    plot_1: {
        'curves': [p1_curve_1, p1_curve_2],
        'widget': graph_widgets[0],
        'legend': legend_widgets[0]
    },
    plot_2: {
        'curves': [p2_curve_1],
        'widget': graph_widgets[1],
        'legend': legend_widgets[1]
    }
}
scalars = {
    freq_1: number_widgets[0],
    sp_1: number_widgets[1],
    lock_1: bool_widgets[0],
    freq_2: number_widgets[2]
}

gui_client.assign_widgets(plots=plots, scalars=scalars)
time.sleep(1)
gui_client.set_scalar(0.5, sp_1)

gui_client.set_scalar(True, lock_1)

for i in range(10000):
    gui_client.set_curve_data(
        np.random.random(1000),
        plot_label=plot_1,
        curve_label=p1_curve_1
    )
    gui_client.set_curve_data(
        1 + np.random.random(1000),
        plot_label=plot_1,
        curve_label=p1_curve_2
    )
    gui_client.set_curve_data(
        np.random.random(1000),
        plot_label=plot_2,
        curve_label=p2_curve_1
    )
    gui_client.set_scalar(
        value=np.random.random_sample(),
        scalar_label=freq_1
    )
    gui_client.set_scalar(
        value=np.random.random_sample(),
        scalar_label=freq_2
    )
    if np.random.random_sample() > 0.5:
        gui_client.set_scalar(
            value=True,
            scalar_label=lock_1
        )
    else:
        gui_client.set_scalar(
            value=False,
            scalar_label=lock_1
        )
