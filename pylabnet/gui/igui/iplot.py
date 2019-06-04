import plotly.graph_objs as go
from pylabnet.gui.output_interface import TraceInterface, HeatMapInterface, PBarInterface
import ipywidgets as iwdgt
from IPython.display import display
import copy
import numpy as np


class SingleTraceFig(TraceInterface):

    def __init__(self, mode='lines', title_str=None):

        self._fig = go.FigureWidget(data=[])

        self._fig.add_scatter(
            x=[],
            y=[],
            mode=mode
        )

        if title_str is not None:
            self._fig.layout.update(title=title_str)

        self._x_ar = np.array([])
        self._y_ar = np.array([])

    def set_data(self, x_ar=None, y_ar=None):

        # Set x_ar
        if x_ar is not None:
            self._x_ar = np.array(
                copy.deepcopy(x_ar)
            )

        # Set y_ar
        if y_ar is not None:
            self._y_ar = np.array(
                copy.deepcopy(y_ar)
            )

        # Update figure
        with self._fig.batch_update():
            self._fig.data[0].x = self._x_ar
            self._fig.data[0].y = self._y_ar

    def append_data(self, x_ar=None, y_ar=None):

        # Append new data to internal arrays
        if x_ar is not None:
            self._x_ar = np.append(self._x_ar, x_ar)

        if y_ar is not None:
            self._y_ar = np.append(self._y_ar, y_ar)

        # Apply changes to the figure
        if x_ar is not None or y_ar is not None:
            with self._fig.batch_update():
                self._fig.data[0].x = self._x_ar
                self._fig.data[0].y = self._y_ar

    def set_lbls(self, x_str=None, y_str=None):

        if x_str is not None:
            self._fig.layout.xaxis.title = x_str

        if y_str is not None:
            self._fig.layout.yaxis.title = y_str

    def show(self):
        display(self._fig)


class HeatMapFig(HeatMapInterface):

    def __init__(self, title_str=None):

        self._fig = go.FigureWidget(data=[])

        self._fig.add_heatmap(
            x=[],
            y=[],
            z=[[], []]
        )

        if title_str is not None:
            self._fig.layout.title = title_str

        self._x_ar = np.array([], dtype=float)
        self._y_ar = np.array([], dtype=float)
        self._z_ar = np.array([], dtype=float)

    def set_data(self, x_ar=None, y_ar=None, z_ar=None):

        # Set x_ar
        if x_ar is not None:
            self._x_ar = np.array(
                copy.deepcopy(x_ar)
            )

        # Set y_ar
        if y_ar is not None:
            self._y_ar = np.array(
                copy.deepcopy(y_ar)
            )

        # Set z_ar
        if z_ar is not None:
            self._z_ar = np.array(
                copy.deepcopy(z_ar)
            )

        # Update figure
        if x_ar is not None or y_ar is not None or z_ar is not None:
            with self._fig.batch_update():
                self._fig.data[0].x = self._x_ar
                self._fig.data[0].y = self._y_ar
                self._fig.data[0].z = self._z_ar

    def append_row(self, y_val=None, z_ar=None):

        if y_val is not None:
            self._y_ar = np.append(self._y_ar, y_val)

        if z_ar is not None:
            self._z_ar = np.append(
                self._z_ar,
                [z_ar],  # wrap into [] to make 2D array
                axis=0
            )

        # Apply changes to the figure
        if y_val is not None or z_ar is not None:
            with self._fig.batch_update():
                self._fig.data[0].y = self._y_ar
                self._fig.data[0].z = self._z_ar

    def append_col(self, x_val=None, z_ar=None):

        if x_val is not None:
            self._x_ar = np.append(self._x_ar, x_val)

        if z_ar is not None:
            self._z_ar = np.append(
                self._z_ar,
                np.transpose([z_ar]),
                axis=1
            )

        # Apply changes to the figure
        if x_val is not None or z_ar is not None:
            with self._fig.batch_update():
                self._fig.data[0].x = self._x_ar
                self._fig.data[0].z = self._z_ar

    def set_lbls(self, x_str=None, y_str=None):

        if x_str is not None:
            self._fig.layout.xaxis.title = x_str

        if y_str is not None:
            self._fig.layout.yaxis.title = y_str

    def show(self):
        display(self._fig)


class PBar(PBarInterface):

    def __init__(self, value=0):
        self._p_bar = iwdgt.FloatProgress()

        self._p_bar.min = 0
        self._p_bar.max = 100

        self.set_value(value=value)

    def set_value(self, value):
        self._p_bar.value = value
        self._p_bar.description = '{:.0f} %'.format(value)

    def show(self):
        display(self._p_bar)


class ComboTraceHMapPBar:

    def __init__(self, trace_title=None, hm_title=None):

        self.trace_fig = SingleTraceFig(title_str=trace_title)
        self.hm_fig = HeatMapFig(title_str=hm_title)
        self.p_bar = PBar()

        self._grid = iwdgt.VBox(
            [
                iwdgt.HBox([self.trace_fig._fig, self.hm_fig._fig]),
                self.p_bar._p_bar
            ]
        )

    def show(self):
        display(self._grid)



