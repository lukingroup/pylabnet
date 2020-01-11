from pylabnet.gui.pyqt.external_gui import Client
import numpy as np


gui_client = Client(host='localhost', port=9)
gui_client.connect()

# x_axis = np.arange(1000)
# y_axis = np.sin(x_axis*2*np.pi/1000)
#
# for i in np.linspace(1000,2000,1000):
#     y_axis = np.append(y_axis[1:], np.sin(i*2*np.pi/1000))
#     gui_client.set_data(y_axis)
#     gui_client.update_output()

gui_client.load_gui()
