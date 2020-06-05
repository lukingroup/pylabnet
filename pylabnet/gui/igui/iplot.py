import plotly.graph_objs as go
from plotly.subplots import make_subplots

from pylabnet.gui.output_interface import MultiTraceInterface, TraceInterface, HeatMapInterface, PBarInterface
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


class MultiTraceFig(MultiTraceInterface):

    def __init__(self, title_str=None, ch_names=None, shot_noise=False, legend_orientation=None):
        """ MultiTraceFig constructor

        :param title_str: string to display for plot title
        :param ch_names: list of channel name strings for multi
            -channel plot
        :param shot_noise: boolean of whether or not to plot
            shot noise on individual traces
        """

        self._fig = go.FigureWidget(data=[])
        self._shot_noise = shot_noise
        self._ch_names = ch_names

        if self._ch_names is not None:

            # Initialize all channels if given
            self._num_ch = 0
            self._allocate_arrays()

        else:
            self._num_ch = 0

        if title_str is not None:
            self._fig.layout.update(title=title_str)

        if legend_orientation is not None:
            self._fig.update_layout(
                legend=dict(x=0, y=1.1),
                legend_orientation=legend_orientation
            )

    def set_data(self, x_ar=None, y_ar=None, ind=0, noise=None):
        """ Sets data to MultiTraceFig instance

        :param x_ar: np array of x-axis data values
        :param y_ar: np array of y-axis data values
        :param ind: index of channels to assign data to
            (index starts from 0)
        :param noise: np array of y-axis error bar sizes
        """

        # First check that data array at particular index has
        # already been allocated, and if not, allocate the
        # previous data arrays
        to_allocate = ind - self._num_ch
        if to_allocate >= 0:
            self._allocate_arrays(
                num_arrays=to_allocate+1
            )

        # Update figure
        if x_ar is not None and y_ar is not None:

            if self._shot_noise:

                if noise is None:
                    noise = 0*y_ar

                # Input shot noise
                x_rev = x_ar[::-1]
                y_upper = y_ar + noise
                y_lower = y_ar - noise
                y_lower = y_lower[::-1]
                with self._fig.batch_update():
                    self._fig.data[ind*2].x = np.hstack((x_ar, x_rev))
                    self._fig.data[ind*2].y = np.hstack((y_upper, y_lower))

                # Now data
                with self._fig.batch_update():
                    self._fig.data[2*ind+1].x = x_ar
                    self._fig.data[2*ind+1].y = y_ar

            else:
                with self._fig.batch_update():
                    self._fig.data[ind].x = x_ar
                    self._fig.data[ind].y = y_ar

    def set_lbls(self, x_str=None, y_str=None):
        """

        :param x_str: x_axis label
        :param y_str: y_axis label
        """

        # Set titles of x and y axes as desired
        if x_str is not None:
            self._fig.layout.xaxis.title = x_str

        if y_str is not None:
            self._fig.layout.yaxis.title = y_str

    def show(self):
        display(self._fig)
        # self._fig.show(renderer="iframe")

    # Technical methods

    def _allocate_arrays(self, num_arrays=None):

        # Color-list
        dflt_plotly_colors = [
            'rgb(31, 119, 180)', 'rgb(255, 127, 14)',
            'rgb(44, 160, 44)', 'rgb(214, 39, 40)',
            'rgb(148, 103, 189)', 'rgb(140, 86, 75)',
            'rgb(227, 119, 194)', 'rgb(127, 127, 127)',
            'rgb(188, 189, 34)', 'rgb(23, 190, 207)'
        ]
        dflt_plotly_colors_lo = [
            'rgba(31, 119, 180, 0.2)', 'rgba(255, 127, 14, 0.2)',
            'rgba(44, 160, 44, 0.2)', 'rgba(214, 39, 40, 0.2)',
            'rgba(148, 103, 189, 0.2)', 'rgba(140, 86, 75, 0.2)',
            'rgba(227, 119, 194, 0.2)', 'rgba(127, 127, 127, 0.2)',
            'rgba(188, 189, 34, 0.2)', 'rgba(23, 190, 207, 0.2)'
        ]

        # If a certain number of arrays to be allocated is not assigned,
        # just allocate the number as given by number of elements in
        if num_arrays is not None:
            for index in range(num_arrays):
                if self._shot_noise:

                    # Generate additional scatter for shot noise bounds
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        name='ch'+str(index),
                        showlegend=False,
                        fill='tozerox',
                        line=dict(color='rgba(255,255,255,0)'),
                        fillcolor=dflt_plotly_colors_lo[index]
                    )
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        mode='lines',
                        name='ch'+str(index),
                        line=dict(color=dflt_plotly_colors[index])
                    )
                else:
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        mode='lines',
                        name='ch'+str(index)
                    )
                self._num_ch += 1

        # Otherwise just use the self._ch_list to allocate arrays
        else:
            for index, channel in enumerate(self._ch_names):
                if self._shot_noise:

                    # Generate additional scatter for shot noise bounds
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        name=channel,
                        showlegend=False,
                        fill='tozerox',
                        line=dict(color='rgba(255,255,255,0)'),
                        fillcolor=dflt_plotly_colors_lo[index]
                    )
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        mode='lines',
                        name=channel,
                        line=dict(color=dflt_plotly_colors[index])
                    )
                else:
                    self._fig.add_scatter(
                        x=[],
                        y=[],
                        mode='lines',
                        name=channel
                    )
                self._num_ch += 1

        def set_data(self, x_ar=None, y_ar=None, trace=0, ind=0, noise=None):
            """ Sets data to MultiTraceFig instance

            :param x_ar: np array of x-axis data values
            :param y_ar: np array of y-axis data values
            :param ind: index of channels to assign data to
                (index starts from 0)
            :param noise: np array of y-axis error bar sizes
            """

            # First check that data array at particular index has
            # already been allocated, and if not, allocate the
            # previous data arrays
            to_allocate = ind - self._num_ch
            if to_allocate >= 0:
                self._allocate_arrays(
                    num_arrays=to_allocate+1
                )

            # Update figure
            if x_ar is not None and y_ar is not None:

                if self._shot_noise:

                    if noise is None:
                        noise = 0*y_ar

                    # Input shot noise
                    x_rev = x_ar[::-1]
                    y_upper = y_ar + noise
                    y_lower = y_ar - noise
                    y_lower = y_lower[::-1]
                    with self._fig.batch_update():
                        self._fig.data[ind*2].x = np.hstack((x_ar, x_rev))
                        self._fig.data[ind*2].y = np.hstack((y_upper, y_lower))

                    # Now data
                    with self._fig.batch_update():
                        self._fig.data[2*ind+1].x = x_ar
                        self._fig.data[2*ind+1].y = y_ar

                else:
                    with self._fig.batch_update():
                        self._fig.data[ind].x = x_ar
                        self._fig.data[ind].y = y_ar



class StaggeredTraceFig():
    """Plot multiple traces in seperate subplots.

    :param ch_names: list of channel name strings for multi
        -channel plot
    """

    def __init__(self, ch_names=None, legend_orientation=None):

        self._num_plots = len(ch_names)
        self._fig = make_subplots(
            rows=self._num_plots,
            cols=1,
            shared_xaxes=True
        )
        self._ch_names = ch_names

        if title_str is not None:
            self._fig.layout.update(title=title_str)

        if ch_names is not None:
            self._fig.update_layout(
                legend=dict(x=-0.2, y=0),
                legend_orientation=legend_orientation
            )

        self._fig['layout'].update(height=100 + 100 * self._num_plots, width=800)
        self._fig['layout']['yaxis'].update(showticklabels=False)
        self._fig['layout']['legend'].update(traceorder='reversed')
        self._fig['layout'].update(hovermode='closest')

    def add_plot_trace(self, x_ar=None, y_ar=None, channel_index=None):
        """Adds plot and sets data to StaggeredTraceFig instance

        :param x_ar: np array of x-axis data values
        :param y_ar: np array of y-axis data values
        :channel_index: index of channels to assign data to
            (index starts from 0)
        """

        # Color-list
        dflt_plotly_colors = [
            'rgb(31, 119, 180)', 'rgb(255, 127, 14)',
            'rgb(44, 160, 44)', 'rgb(214, 39, 40)',
            'rgb(148, 103, 189)', 'rgb(140, 86, 75)',
            'rgb(227, 119, 194)', 'rgb(127, 127, 127)',
            'rgb(188, 189, 34)', 'rgb(23, 190, 207)'
        ]
        dflt_plotly_colors_lo = [
            'rgba(31, 119, 180, 0.2)', 'rgba(255, 127, 14, 0.2)',
            'rgba(44, 160, 44, 0.2)', 'rgba(214, 39, 40, 0.2)',
            'rgba(148, 103, 189, 0.2)', 'rgba(140, 86, 75, 0.2)',
            'rgba(227, 119, 194, 0.2)', 'rgba(127, 127, 127, 0.2)',
            'rgba(188, 189, 34, 0.2)', 'rgba(23, 190, 207, 0.2)'
        ]

        self._fig.append_trace(
            go.Scatter(
                    x=x_ar,
                    y=y_ar,
                    mode='lines',
                    name=self._ch_names[channel_index]
            ),
            row=channel_index+1,
            col=1
        )

    def show(self):
        display(self._fig)


    def set_lbls(self, x_str=None, y_str=None):
        """

        :param x_str: x_axis label
        :param y_str: y_axis label
        """

        # Set titles of x and y axes as desired
        if x_str is not None:
            # Update xaxis properties
            self._fig.update_xaxes(title_text=x_str, row=self._num_plots, col=1)

        if y_str is not None:
            self._fig.update_yaxes(title_text=y_str, row=int(self._num_plots / 2)+1, col=1)


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

def main():
    ch_names = ['CH1', 'CH2']
    iplt = StaggeredTraceFig(ch_names=ch_names)

    iplt.show()
    iplt.add_plot_trace(
        x_ar=np.zeros(5),
        y_ar=np.zeros(5),
        channel_index=0
    )

if __name__ == '__main__':
    main()