"""
Module for creating a standalone GUI window that can be accessed remotely via the pylabnet client-server interface.

Templates for the GUI window can be configured using Qt Designer and should be stored as .ui files in the
./gui_templates directory.
"""

from PyQt5 import QtWidgets, uic
import pyqtgraph as pg

from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase

import numpy as np
import os
import sys
import pickle


class Window(QtWidgets.QMainWindow):
    """
    Main window for GUI. This should be instantiated locally to create a GUI window.

    An app should be instantiated prior to a Window, as below:
        app = QtWidgets.QApplication(sys.argv)
        main_window = Window(app, gui_template="my_favorite_gui")
    """

    _gui_directory = "gui_templates"
    _default_template = "mainwindow"
    _color_list = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',
                   '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
                   '#000075', '#808080']

    def __init__(self, app, gui_template=None, run=True):
        """
        Instantiates main window object.

        :param app: instance of QApplication class - must be instantiated prior to Window
        :param gui_template: (str, optional) name of gui template to use
        :param run: (bool, optional) whether or not to run (display) the GUI upon instantiation
        """

        super(Window, self).__init__()

        self._ui = None
        self._app = app
        self._is_running = False
        self.plots = {}
        self.curves = {}
        self.errors = {}
        self.legends = {}
        self.pens = {}

        # Load and run the GUI
        self._load_gui(gui_template=gui_template, run=run)

    def close_gui(self):
        """
        Stops GUI without crashing. Does not physically close the window, but after execution of this statement,
        it is safe to close the window.
        """

        sys.exit(self._app.exec_())

    def assign_plot(self, plot_widget=None, legend_widget=None, plot_label=None, curve_label=None, error_bars=False):
        """
        Assigns a plot with the key plot_label to the variable self.plot_widget. Example:
            >> main_window.assign_plot("plot_widget_1", plot_label="Channel 1 Monitor")
        Here, "plot_widget_1" refers to a widget object in main_window, as specified in the .ui file

        :param plot_widget: (str) variable name of the plot to be assigned. Should only be passed the first time for
            each plot widget in the GUI. After that, the plot_label can be used to reference the plot
        :param legend_widget: (str, optional) variable name of the GraphicsView container for the legend. If this is not
            provided on the first assignment to a new plot widget, a legend will not be shown.
        :param plot_label: (str, optional) reference name of the plot. By default plot_label is set to plot_widget.
            plot_label is used as the title for the plot.
        :param curve_label: (str, optional) reference name of the curve on the plot. Only relevant for plots which have
            more than one curve. In that case, curve_label is used both to identify which curve to set data to in future
            calls of the set_plot_data() method, as well as in the plot legend
        :param error_bars: (bool, optional) determines whether or not the plot will have error bars
        """

        # Set a default plot_label if not provided
        if plot_label is None:
            plot_label = plot_widget

        # Assign plot widget object to plot_label key in self.plots
        # getattr(Obj, str) is used to find the attribute of Obj with a particular name (str)
        if plot_widget is not None:
            self.plots[plot_label] = getattr(self, plot_widget)

            # Set plot legend and title
            self.plots[plot_label].setTitle(plot_label)
            self._set_legend(legend_widget=legend_widget, plot_label=plot_label)

        # Count how many times this plot_label has been used based on the existing list of curves
        curve_index = sum(1 for plot_heading in self.curves.keys() if plot_label in plot_heading)

        # If no curve label is given, assign default numerical curve name based on number of curve
        if curve_label is None:
            curve_label = "curve_"+str(curve_index)

        # Assign pen and curve objects to plot_label+'_'+curve_label key in self.curves and self.pens
        # Set curve style
        curve_key = plot_label+'_'+curve_label
        self.pens[curve_key] = pg.mkPen(
            self._color_list[len(self.pens)]
        )
        self.curves[curve_key] = self.plots[plot_label].plot(
            pen=self.pens[curve_key]
        )

        # Initialize error bars if necessary
        if error_bars:
            self.errors[curve_key] = pg.ErrorBarItem(
                pen=self.pens[curve_key],
                beam=1
            )
            self.plots[plot_label].addItem(self.errors[curve_key])

        self.legends[plot_label].addItem(self.curves[curve_key], name=curve_label)

    def set_data(self, data, error=None, plot_label=None, curve_label=str(0)):

        # Check that the plot_label is reasonable
        if plot_label is not None and plot_label in self.plots:

            # Update data
            curve_key = plot_label + '_' + curve_label
            self.curves[curve_key].setData(data)

            # We need to do some type handling for error bars since the data must be format as x, y
            if error is not None:
                if len(data.shape) == 1:
                    x, y = np.arange(len(data)), data
                else:
                    x, y = data[0], data[1]
                self.errors[curve_key].setData(x=x, y=y, height=error)

    # Technical methods

    def _load_gui(self, gui_template=None, run=True):
        """
        Loads a GUI template to the main window.

        Currently assumes all templates are in the directory given by the self._gui_directory attribute. If no
        gui_template is passed, the self._default_template is used. By default, this method also runs the GUI window.

        :param gui_template: name of the GUI template to use (str)
        :param run: whether or not to also run the GUI (bool)
        """

        if gui_template is None:
            gui_template = self._default_template

        # Check for proper formatting
        if not gui_template.endswith(".ui"):
            gui_template += ".ui"

        # Find path to GUI
        # Currently assumes all templates are in the directory given by the self._gui_directory attribute
        self._ui = os.path.join(os.getcwd(), self._gui_directory, gui_template)

        # Load UI
        uic.loadUi(self._ui, self)

        if run:
            self._is_running = True
            self._run_gui()

    def _run_gui(self):
        """Runs the GUI. Displays the main window"""

        self.show()

    def _set_legend(self, legend_widget=None, plot_label=None):
        """
        Sets the legend for a plot. Should be invoked once at the beginning when a plot is initialized. Requires a
        GraphicsView instance in order to serve as a container for the legend. This can be done by dragging a
        QGraphicsView object into the desired shape and location in the GUI, and promoting to a GraphicsView object
        with the pyqtgraph header. The legend is configured to sit in the top left corner of the box.

        :param legend_widget: (str, optional) variable name of the GraphicsView container for the legend. If this is not
            provided on the first assignment to a new plot widget, a legend will not be shown.
        :param plot_label: (str, optional) reference name of the plot. By default plot_label is set to plot_widget
        """
        # Initialize legend display
        if legend_widget is not None and plot_label is not None:
            # Assign legend widget to plot_label key in self.legends
            self.legends[plot_label] = pg.LegendItem()

            # Assign legend widget to GraphicsView instance provided using a ViewBox object as an anchor
            # Simply tying the legend to the plot causes it to overlap with the data
            # Not sure this is the best way to solve this, but this solution enables .ui defined legend placement
            view_box = pg.ViewBox()
            getattr(self, legend_widget).setCentralWidget(view_box)
            self.legends[plot_label].setParentItem(view_box)
            self.legends[plot_label].anchor((0, 0), (0, 0))


# TODO: Implement client and service

class Service(ServiceBase):
    pass


class Client(ClientBase):
    pass
