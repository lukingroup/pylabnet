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
import pickle
import copy


class Window(QtWidgets.QMainWindow):
    """
    Main window for GUI. This should be instantiated locally to create a GUI window.

    An app should be instantiated prior to a Window, as below:
        app = QtWidgets.QApplication(sys.argv)
        main_window = Window(app, gui_template="my_favorite_gui")
    """

    _gui_directory = "gui_templates"
    _default_template = "mainwindow"

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
        self.scalars = {}
        self._plots_to_assign = []
        self._curves_to_assign = []
        self._scalars_to_assign = []
        self._curves_to_remove = []

        # Load and run the GUI
        self._load_gui(gui_template=gui_template, run=run)

    def assign_widgets(self, plots, scalars):
        """
        Adds all plots and widget configurations to assignment queue in one step. This is for convenience, to be used
        at the beginning of a script. Plots and curves can still be assigned later on using the individual assign_plot,
        assign_curve, and assign_scalar methods.

        :param plots: (dict) dictionary of curves to assign to the GUI. Keys are used as plot titles and are also used
            to reference plots in future calls (e.g. set_curve_data). Values are another dictionary with two keys:
            'curves' and 'widgets'. Values associated with 'curves' are a list of curve name strings, which are used as
            name references and in plot legends. These should be chosen at the script writing stage to be application
            specific and to allow the developer to conveniently refer to a particular plot and curve. Values associated
            with 'widget' are names of instances of PlotWidget in the GUI. Values of 'legend' are names of instances of
            GraphicsView widgets in the GUI. Instances of widgets should be defined when developing the .gui file in
            QtDesigner, and should generally be given variable names that are agnostic to the specific application.
            Example input:
                {'Velocity Monitor': {'curves': ['Velocity', 'Velocity setpoint'],
                                      'widget': 'graph_widget_1', 'legend': 'legend_widget_1'},
                 'TiSa Monitor': {'curves': ['TiSa'], 'widget': 'graph_widget_2', 'legend': 'legend_widget_2'}}
        :param scalars: (dict) dictionary of scalars (numerical values, booleans) revealing mapping between scalar
            labels and instances of widgets in the GUI. Instances of GUI widgets should be defined when developing the
            .gui file in QtDesigner, and should generally be given variable names that are agnostic to the specific
            application. Script specific names are defined as scalar labels (keys). Values should be a string - the
            variable name for the Widget instance (e.g. QLCDNumber or QCheckbox). Example:
                {'Velocity Frequency': 'number_widget_1', 'Velocity Setpoint': 'number_widget_2',
                 'Velocity Lock': 'boolean_widget_1', 'TiSa Frequency': 'number_widget_3'}
        """

        # Iterate through all plots and curves
        for plot, plot_dict in plots.items():

            # First instantiate this plot
            self.assign_plot(
                plot_widget=plot_dict['widget'],
                plot_label=plot,
                legend_widget=plot_dict['legend']
            )

            # Now assign all curves
            for curve in plot_dict['curves']:
                self.assign_curve(
                    plot_label=plot,
                    curve_label=curve
                )

        # Next, assign all scalars
        for scalar_name, scalar_widget in scalars.items():
            self.assign_scalar(
                scalar_widget=scalar_widget,
                scalar_label=scalar_name
            )

    def assign_plot(self, plot_widget, plot_label, legend_widget):
        """
        Adds plot assignment request to a queue

        :param plot_widget: (str) name of the plot widget to use in the GUI window
        :param plot_label: (str) label to use for future referencing of the plot widget from the self.plots dictionary
        :param legend_widget: (str) name of the pg.GraphicsView instance for use as a legend
        """

        self._plots_to_assign.append((plot_widget, plot_label, legend_widget))

    def assign_curve(self, plot_label, curve_label):
        """Adds curve assignment to the queue"""

        self._curves_to_assign.append((plot_label, curve_label))

    def remove_curve(self, plot_label, curve_label):
        """
        Adds a curve removal request to the queue

        :param plot_label: (str) name of plot holding the curve
        :param curve_label: (str) name of the curve to remove
        """

        self._curves_to_remove.append((plot_label, curve_label))

    def assign_scalar(self, scalar_widget, scalar_label):
        """
        Adds scalar assignment request to the queue

        :param scalar_widget: (str) name of the scalar object (e.g. QLCDNumber) in the GUI
        :param scalar_label: (str) label for self.numbers dictionary
        """
        self._scalars_to_assign.append((scalar_widget, scalar_label))

    def set_curve_data(self, data, plot_label, curve_label, error=None):
        """Sets data to a specific curve (does not update GUI directly)

        :param data: (np.array) 1D or 2D numpy array with data
        :param plot_label: (str) label of the plot
        :param curve_label: (str) curve key of curve to set
        :param error: (np.array, optional) 1D array with error bars, if applicable
        """

        self.plots[plot_label].curves[curve_label].set_curve_data(data, error=error)

    def set_scalar(self, value, scalar_label):
        """Sets the value of a numerical display internally (does not update)"""
        self.scalars[scalar_label].set_data(value)

    def configure_widgets(self):
        """Configures all widgets in the queue"""

        # Assign plot widgets
        for plot_widget_params in self._plots_to_assign:

            # Unpack parameters
            plot_widget, plot_label, legend_widget = plot_widget_params

            # Assign plot to physical plot widget in GUI
            try:
                self._assign_plot(plot_widget, plot_label, legend_widget)
                self._plots_to_assign.remove(plot_widget_params)
            except KeyError:
                pass

        # Assign curves to plots
        for curve_params in self._curves_to_assign:

            # Unpack parameters
            plot_label, curve_label = curve_params

            # Assign curve to physical plot widget in GUI
            try:
                self._assign_curve(plot_label, curve_label)
                self._curves_to_assign.remove(curve_params)
            except KeyError:
                pass

        # Assign scalar widgets
        for scalar_params in self._scalars_to_assign:

            # Unpack parameters
            scalar_widget, scalar_label = scalar_params

            # Assign scalar to physical scalar widget in GUI
            try:
                self._assign_scalar(scalar_widget, scalar_label)
                self._scalars_to_assign.remove(scalar_params)
            except KeyError:
                pass

        for curve_params in self._curves_to_remove:

            # Unpack parameters
            plot_label, curve_label = curve_params

            try:
                self._remove_curve(plot_label, curve_label)
                self._curves_to_remove.remove(curve_params)
            except KeyError:
                pass

    def update_widgets(self):
        """Updates all widgets on the physical GUI to current data"""

        # Update all plots
        for plot in self.plots.values():
            plot.update_output()

        # Update all scalars
        for scalar in self.scalars.values():
            scalar.update_output()

    def force_update(self):
        """
        Forces the GUI to update

        :return: 0 when complete
        """

        # self.configure_widgets()
        # self.update_widgets()
        self._app.processEvents()
        return 0

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
        self._ui = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self._gui_directory,
            gui_template
        )

        # Load UI
        uic.loadUi(self._ui, self)

        if run:
            self._is_running = True
            self._run_gui()

    def _run_gui(self):
        """Runs the GUI. Displays the main window"""

        self.show()

    def _force_update(self):
        self._app.processEvents()

    def _assign_plot(self, plot_widget, plot_label, legend_widget):
        """
        Assigns a plot to a particular plot widget

        :param plot_widget: (str) name of the plot widget to use in the GUI window
        :param plot_label: (str) label to use for future referencing of the plot widget from the self.plots dictionary
        :param legend_widget: (str) name of the GraphicsView widget to use in the GUI window for this plot legend
        """

        self.plots[plot_label] = Plot(self, plot_widget, legend_widget)

        # Set title
        self.plots[plot_label].widget.setTitle(plot_label)

    def _assign_curve(self, plot_label, curve_label):
        """
        Assigns a curve to a plot

        :param plot_label: (str) label of the plot to assign
        :param curve_label: (str) label of curve to use for indexing in the self.plots[plot_label].curves dictionary
        """

        self.plots[plot_label].add_curve(curve_label)

    def _remove_curve(self, plot_label, curve_label):
        """
        Removes a curve from a plot

        :param plot_label: (str) label of plot holding curve
        :param curve_label: (str) label of curve to remove
        """

        self.plots[plot_label].remove_curve(curve_label)
        self._force_update()

    def _assign_scalar(self, scalar_widget, scalar_label):
        """
        Assigns scalar widget display in the GUI

        :param scalar_widget: (str) name of the scalar widget (e.g. QLCDNumber) in the GUI
        :param scalar_label: (str) label of the scalar widget
        """
        self.scalars[scalar_label] = Scalar(self, scalar_widget)


class Service(ServiceBase):

    def exposed_assign_widgets(self, plots_pickle, scalars_pickle):
        plots = pickle.loads(plots_pickle)
        scalars = pickle.loads(scalars_pickle)
        return self._module.assign_widgets(
            plots=plots,
            scalars=scalars
        )

    def exposed_assign_plot(self, plot_widget, plot_label, legend_widget):
        return self._module.assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    def exposed_assign_curve(self, plot_label, curve_label):
        return self._module.assign_curve(
            plot_label=plot_label,
            curve_label=curve_label
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

    def exposed_set_curve_data(self, data_pickle, plot_label, curve_label, error_pickle=None):
        data = pickle.loads(data_pickle)
        error = pickle.loads(error_pickle)
        return self._module.set_curve_data(
            data=data,
            plot_label=plot_label,
            curve_label=curve_label,
            error=error
        )

    def exposed_set_scalar(self, value, scalar_label):
        return self._module.set_scalar(
            value=value,
            scalar_label=scalar_label
        )

    def exposed_force_update(self):
        return self._module.force_update()


class Client(ClientBase):

    def assign_widgets(self, plots, scalars):
        plots_pickle = pickle.dumps(plots)
        scalars_pickle = pickle.dumps(scalars)
        return self._service.exposed_assign_widgets(
            plots_pickle=plots_pickle,
            scalars_pickle=scalars_pickle
        )

    def assign_plot(self, plot_widget, plot_label, legend_widget):
        return self._service.exposed_assign_plot(
            plot_widget=plot_widget,
            plot_label=plot_label,
            legend_widget=legend_widget
        )

    def assign_curve(self, plot_label, curve_label):
        return self._service.exposed_assign_curve(
            plot_label=plot_label,
            curve_label=curve_label
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
        return self._service.exposed_set_scalar(
            value=value,
            scalar_label=scalar_label
        )

    def force_update(self):
        return self._service.exposed_force_update()


class Plot:

    _color_list = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',
                   '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
                   '#000075', '#808080']

    def __init__(self, gui, plot_widget, legend_widget):
        """
        Instantiates plot object for a plot inside of the GUI window

        :param gui: (Window) instance of the GUI window
        :param plot_widget: (str) name of the plot widget
        :param legend_widget: (str) name of the legend widget
        """

        self.gui = gui
        self.widget = getattr(self.gui, plot_widget)
        self.curves = {}
        self.legend = None

        # Set up legend
        self._set_legend(legend_widget=legend_widget)

    def add_curve(self, curve_label):
        """
        Add a curve to the plot

        :param curve_label: (str) instance of curve class to add to the plot
        """

        # Add a new curve to self.curves dictionary for this plot
        self.curves[curve_label] = Curve(
            self.widget,
            pen=pg.mkPen(color=self._color_list[len(self.curves)])
        )

        # Configure legend
        self._add_to_legend(curve_label)

    def remove_curve(self, curve_label):
        """
        Removes a curve from the plot

        :param curve_label: (str) name of curve to remove
        """

        # Remove from legend
        self._remove_from_legend(curve_label)

        # Remove from plot
        self.widget.removeItem(self.curves[curve_label].widget)

        # Remove from dictionary of curves
        del self.curves[curve_label]

    def update_output(self):
        """Updates plot output to latest data"""

        for curve in self.curves.values():
            curve.widget.setData(
                curve.data,
                error=curve.error
            )

    # Technical methods

    def _set_legend(self, legend_widget):
        """
        Sets the legend for a plot. Should be invoked once at the beginning when a plot is initialized. Requires a
        GraphicsView instance in order to serve as a container for the legend. This can be done by dragging a
        QGraphicsView object into the desired shape and location in the GUI, and promoting to a GraphicsView object
        with the pyqtgraph header. The legend is configured to sit in the top left corner of the box.

        :param legend_widget: (str) name of GraphicsView instance in the GUI window to store legend in
        """

        # Assign legend widget to plot_label key in self.legends
        self.legend = pg.LegendItem()

        # Assign legend widget to GraphicsView instance provided using a ViewBox object as an anchor
        # Simply tying the legend to the plot causes it to overlap with the data
        # Not sure this is the best way to solve this, but this solution enables .ui defined legend placement
        view_box = pg.ViewBox()
        getattr(self.gui, legend_widget).setCentralWidget(view_box)
        self.legend.setParentItem(view_box)
        self.legend.anchor((0, 0), (0, 0))

    def _add_to_legend(self, curve_label):
        """
        Adds a curve to the legend

        :param curve_label: (str) key label of curve in self.curves dictionary to add to legend
        """

        # Add some space to the legend to prevent overlapping
        self.legend.addItem(self.curves[curve_label].widget, ' - '+curve_label)

    def _remove_from_legend(self, curve_label):
        """
        Removes a curve from the legend

        :param curve_label: (str) label of curve to remove from legend
        """
        self.legend.removeItem(self.curves[curve_label].widget)


class Curve:

    def __init__(self, plot_widget, pen=None, error=False):
        """
        Instantiates a curve inside of a plot_widget

        :param plot_widget: (pg.PlotItem) instance of plot widget to add curve to
        :param pen: (pg.Pen) pen to use to draw curve
        :param error: (bool, optional) whether or not to add error bars to this plot
        """

        # Instantiate new curve in the plot
        self.widget = plot_widget.plot(pen=pen)

        # Instantiate error bars
        self.error = None
        if error:
            self.error = pg.ErrorBarItem(
                pen=pen
            )
            plot_widget.addItem(self.error)

        self.data = np.array([])
        self.error_data = np.array([])

    def set_curve_data(self, data, error=None):
        """
        Stores data to a new curve

        :param data: (np.array) either a 1D (only y-axis) or 2D (x-axis, y-axis) numpy array
        :param error: (np.array, optional) 1D array for error bars
        """

        self.data = data

        if self.error is not None:
            self.error_data = error


class Scalar:
    """A scalar display object (number or boolean)"""

    def __init__(self, gui, scalar_widget):
        """
        Initializes the scalar widget

        :param gui: (Window) instance of the GUI window class containing the number widget
        :param scalar_widget: (str) name of the widget for reference
        """

        self.data = None
        self.widget = getattr(gui, scalar_widget)

    def set_data(self, data):
        """
        Sets the value of the number internally

        :param data: number to set to
        """
        self.data = data

    def update_output(self):
        """Updates the physical output of the scalar widget."""

        # Set the state, checking first whether it is a boolean display or not
        if isinstance(self.data, bool):
            # Check the state of the button
            if self.widget.isChecked() != self.data:
                self.widget.toggle()
        elif self.data is not None:
            if self.widget.value() != self.data:
                display_str = copy.deepcopy('%.6f' % self.data)
                self.widget.display(display_str)
