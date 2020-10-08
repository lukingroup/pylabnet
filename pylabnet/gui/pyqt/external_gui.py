""" Module for creating a GUI window.

Templates for the GUI window can be configured using Qt Designer and should be stored as .ui files in the
./gui_templates directory.

The GUI is designed to hold a number of user (external script) assigned widget attributes (plots, scalars, labels),
and continuously refresh output. A client can access the GUI through the following types of methods:

- Configuration methods: methods to configure widgets. These include assignment of items in the script to specific
    widgets in the GUI, or changing properties of a specific GUI widget. Configuration calls are added to a queue
    and updated directly in the process containing the GUI server, so they are not implemented directly when called
    by the script.
    ^^^ AS A RESULT, SCRIPTS SHOULD ERROR HANDLE WHEN ACCESSING THE GUI IN THE CASE THAT THE CONFIGURATION REQUEST HAS
    NOT BEEN COMPLETED. This can usually be done by checking a KeyError exception, since the gui module uses dicts
    to access configured widgets, but there may be other exceptions depending on the exact implementation
- Data update methods: methods that update the data for various widgets. Again, for reasons described above, these do
    not directly update the output widget but rather an attribute of the specific widget class (Plot, Scalar, etc). The
    thread running the GUI server continuously updates the widget data to the current value of the attribute.
- Activation/deactivation methods: these activate and deactivate the GUI's update to pull from their internal data
    attribute or not. If a GUI widget is active, it continuously sets its output to widget_instance.data (which can be
    externally modified using data update methods). If a GUI widget is inactive, a user can in principle modify data
    from the GUI window.
- Data pull requests: current GUI widget data values are returned to an external script. These should be used to check
    for updates through the GUI window and to change script parameters as a result.

For error handling, all gui update requests should be enclosed in a try/except statement catching the EOFError which
would be thrown in case the GUI crashes. This enables scripts to continue running even if the GUI crashes.
"""

from PyQt5 import QtWidgets, uic, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import os
import pickle
import copy
import sys
import socket
import ctypes

from pylabnet.network.core.client_base import ClientBase

# Should help with scaling issues on monitors of differing resolution
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class Window(QtWidgets.QMainWindow):
    """ Main window for GUI.

    This should be instantiated locally to create a GUI window. An app should ALWAYS be instantiated prior to a Window,
    as below:
        app = QtWidgets.QApplication(sys.argv)
        main_window = Window(app, gui_template="my_favorite_gui")
    """

    # '#ffe119', 
    _gui_directory = "gui_templates"
    _default_template = "count_monitor"
    COLOR_LIST = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',
                   '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
                   '#000075', '#808080']

    def __init__(self, app=None, gui_template=None, run=True, host=None, port=None, auto_close=True):
        """ Instantiates main window object.

        :param app: instance of QApplication class - MUST be instantiated prior to Window
        :param gui_template: (str, optional) name of gui template to use. By default uses self._default_template. Only
            the filename is required (no filepath or extension)
        :param run: (bool, optional) whether or not to run (display) the GUI upon instantiation. Can set to false in
            order to debug and access Window methods directly in an interactive session
        """

        self.app = app  # Application instance onto which to load the GUI.

        if self.app is None:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setWindowIcon(
                QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
            )

        # Initialize parent class QWidgets.QMainWindow
        super(Window, self).__init__()

        self._ui = None  # .ui file to use as a template


        # Holds all widgets assigned to the GUI from an external script
        # Reference is by keyword (widget_label), and the keyword can be used to access the widget once assigned
        self.plots = {}
        self.scalars = {}
        self.labels = {}
        self.event_buttons = {}
        self.containers = {}
        self.auto_close = auto_close

        # Configuration queue lists
        # When a script requests to configure a widget (e.g. add or remove a plot, curve, scalar, or label), the request
        # is added to this list and can be implemented by the GUI when it is ready. This prevents overloading the
        # client-server interface
        self._plots_to_assign = []
        self._plots_to_remove = []
        self._curves_to_assign = []
        self._scalars_to_assign = []
        self._labels_to_assign = []
        self._buttons_to_assign = []
        self._containers_to_assign = []
        self._curves_to_remove = []

        # List of Numerical widgets for future use in dynamical step size updating
        self.num_widgets = None

        # Load and run the GUI
        self._load_gui(gui_template=gui_template, run=run)
        self.showNormal()

        self.host=None
        self.port=None

        # Confgiure stop button, host and port
        try:
            self.stop_button.clicked.connect(self.close)
            if host is not None:
                self.ip_label.setText(f'IP Address: {host}')
                self.host = host
            if port is not None:
                self.port_label.setText(f'Port: {port}')
                self.port = port
        except:
            pass

    def set_network_info(self, host=None, port=None):
        """ Sets IP and port labels

        :param host: (str) host IP address
        :param port: (int) port number
        """

        if host is not None:
            self.host=host
            self.ip_label.setText(f'IP Adress: {host}')

        if port is not None:
            self.port=port
            self.port_label.setText(f'Port: {port}')

    def add_graph(self, graph_layout=None, index=None):
        """ Adds a new pyqtgraph to a graph layout and returns
        
        :param graph_layout: (str) name of graph layout to add to
        :param index: (int) index if inserting into layout at a
            particular location
        """

        if graph_layout is None:
            layout = getattr(self, 'graph_layout')
        else:
            layout = getattr(self, graph_layout)

        graph = pg.PlotWidget()
        if index is None:
            layout.addWidget(graph)
        else:
            layout.insertWidget(index, graph)

        return graph
    
    def closeEvent(self, event):
        """ Occurs when window is closed. Overwrites parent class method"""

        if self.auto_close:
            try:
                close_client = ClientBase(
                    host=self.host,
                    port=self.port
                )
                close_client.close_server()
            except:
                pass

        self.stop_button.setChecked(True)

    def assign_plot(self, plot_widget, plot_label, legend_widget):
        """ Adds plot assignment request to a queue

        :param plot_widget: (str) name of the plot widget to use in the GUI window
        :param plot_label: (str) label to use for future referencing of the plot widget from the self.plots dictionary
        :param legend_widget: (str) name of the pg.GraphicsView instance for use as a legend
        """

        self._plots_to_assign.append((plot_widget, plot_label, legend_widget))

    def clear_plot(self, plot_widget):
        """ Clears all curves and legend items from a plot

        :param plot_widget: (str) name of the plot widget (instance of PYQTgraph) to clear
        """
        self._plots_to_remove.append(plot_widget)

    def assign_curve(self, plot_label, curve_label, error=False):
        """Adds curve assignment to the queue

        :param plot_label: (str) key of plot to assign curve to
        :param curve_label: (str) key to use for curve assignment + legend
        :param error: (bool, optional) whether or not to use error bars
        """

        self._curves_to_assign.append((plot_label, curve_label, error))

    def remove_curve(self, plot_label, curve_label):
        """ Adds a curve removal request to the queue

        :param plot_label: (str) name of plot holding the curve
        :param curve_label: (str) name of the curve to remove
        """

        self._curves_to_remove.append((plot_label, curve_label))

    def assign_scalar(self, scalar_widget, scalar_label):
        """ Adds scalar assignment request to the queue

        :param scalar_widget: (str) name of the scalar object (e.g. QLCDNumber) in the GUI
        :param scalar_label: (str) label for self.numbers dictionary
        """
        self._scalars_to_assign.append((scalar_widget, scalar_label))

    def assign_label(self, label_widget, label_label):
        """ Adds label widget assignment to queue

        :param label_widget: (str) name of label object (e.g. QLabel) in the GUI
        :param label_label: (str) label for self.labels dictionary
        """
        self._labels_to_assign.append((label_widget, label_label))

    def assign_event_button(self, event_widget, event_label):
        """ Adds button assignment request to the queue

        :param event_widget: (str) physical widget name on the .ui file
        :param event_label: (str) keyname to assign to this button for future reference
        """
        self._buttons_to_assign.append((event_widget, event_label))

    def assign_container(self, container_widget, container_label):
        """ Adds Container assignment request to the queue

        Only QListWidget supported so far
        :param container_widget: (str) physical widget name on the .ui file
        :param container_label: (str) keyname to assign to the widget for future reference
        """
        self._containers_to_assign.append((container_widget, container_label))

    def set_curve_data(self, data, plot_label, curve_label, error=None):
        """ Sets data to a specific curve (does not update GUI directly)

        :param data: (np.array) 1D or 2D numpy array with data
        :param plot_label: (str) label of the plot
        :param curve_label: (str) curve key of curve to set
        :param error: (np.array, optional) 1D array with error bars, if applicable
        """

        self.plots[plot_label].curves[curve_label].set_curve_data(data, error=error)

    def set_scalar(self, value, scalar_label):
        """ Sets the value of a numerical display internally (does not update)"""
        self.scalars[scalar_label].set_data(value)

    # No decorator here because function returns value
    def get_scalar(self, scalar_label):
        """ Returns the data associated with a scalar

        :return: scalar data
        """

        return self.scalars[scalar_label].get_data()

    def activate_scalar(self, scalar_label):
        """ Tells a scalar to pull data from internal self.data attribute

        :param scalar_label: (str) key for relevant scalar
        """
        self.scalars[scalar_label].activate()

    def deactivate_scalar(self, scalar_label):
        """ Tells a scalar not to update output based on self.data attribute

        :param scalar_label: (str) key for relevant scalar
        """
        self.scalars[scalar_label].deactivate()

    def set_label(self, text, label_label):
        """ Sets a label widgets text

        :param text: (str) Text to set
        :param label_label: (str) Key for the label to set
        """
        self.labels[label_label].set_label(text)

    def get_text(self, label_label):
        """ Returns the text in a textual label widget """

        return self.labels[label_label].get_label()

    def was_button_pressed(self, event_label):
        """ Returns whether or not an event button was pressed

        :param event_label: (str) key for button to check
        """

        try:
            return self.event_buttons[event_label].get_state()

        #If the button has not been assigned, just return false
        except KeyError:
            return False

    def was_button_released(self, event_label):
        """ Returns whether or not an event button was released

        :param event_label: (str) key for button to check
        """

        return self.event_buttons[event_label].get_release_state()

    def is_pressed(self, event_label):
        """ Returns whether or not a button is pressed down

        :return: (bool)
        """

        return self.event_buttons[event_label].is_pressed()

    def reset_button(self, event_label):
        """ Resets button internal registers to false

        :param event_label: (str) key for button to check
        """

        self.event_buttons[event_label].reset_button()

    def change_button_background_color(self, event_label, color):
        """ Change background color of button

        :param event_label: (str) key for button to change
        :param color: (str) color to change to
        """
        self.event_buttons[event_label].change_background_color(color)

    def set_button_text(self, event_label, text):
        """ Change button text

        :param event_label: (str) key for button to change
        :param text: (str) text to set to
        """

        self.event_buttons[event_label].set_text(text)

    def get_container_info(self, container_label):
        return self.containers[container_label].get_items()

    def get_item_text(self, container_label):
        return self.containers[container_label].get_current_text()

    def get_item_index(self, container_label):
        return self.containers[container_label].get_current_index()

    def set_item_index(self, container_label, index):
        self.containers[container_label].set_item_index(index)

    # Methods to be called by the process launching the GUI

    def configure_widgets(self):
        """ Configures all widgets in the queue

        Simply passes if the widget does not exist in the GUI
        """

        # Clear plot widgets
        for plot_widget in self._plots_to_remove:

            # Remove plot widget
            try:
                self._clear_plot(plot_widget)
                self._plots_to_remove.remove(plot_widget)
            except KeyError:
                pass

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
            plot_label, curve_label, error = curve_params

            # Assign curve to physical plot widget in GUI
            try:
                self._assign_curve(plot_label, curve_label, error)
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

        # Assign label widgets
        for label_params in self._labels_to_assign:

            # Unpack parameters
            label_widget, label_label = label_params

            # Assign label to physical label widget in GUI
            try:
                self._assign_label(label_widget, label_label)
                self._labels_to_assign.remove(label_params)
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

        for event_button in self._buttons_to_assign:

            # Unpack parameters
            event_widget, event_label = event_button

            try:
                self._assign_event_button(event_widget, event_label)
                self._buttons_to_assign.remove(event_button)
            except KeyError:
                pass

        for cont in self._containers_to_assign:

            # Unpack parameters
            container_widget, container_label = cont

            try:
                self._assign_container(container_widget, container_label)
                self._containers_to_assign.remove(cont)
            except KeyError:
                pass

    def update_widgets(self):
        """ Updates all widgets on the physical GUI to current data"""

        # Update all plots
        for plot in self.plots.values():
            plot.update_output()

        # Update all scalars
        for scalar in self.scalars.values():
            scalar.update_output()

    def force_update(self):
        """ Forces the GUI to update.

        MUST be called in order for the GUI to be responsive, otherwise it freezes

        :return: 0 when complete
        """
        self.app.processEvents()
        return 0

    # Technical methods

    def _load_gui(self, gui_template=None, run=True):
        """ Loads a GUI template to the main window.

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
        try:
            uic.loadUi(self._ui, self)
        except FileNotFoundError:
            raise

        self._initialize_step_sizes()

        if run:
            self._run_gui()

    def _initialize_step_sizes(self):
        """ Initializes all QDoubleSpinBox step sizes based on step_sizes widget

        If step_sizes widget is not present, does nothing and initializes self.num_widgets to None
        """

        # Get all numerical widgets in the GUI
        self.num_widgets = [widget for widget in self.__dict__.values() if isinstance(widget, QtWidgets.QDoubleSpinBox)]
        try:

            # Exclude the step size setting
            self.num_widgets.remove(self.step_size)

            # Get current step size
            step_size = self.step_size.value()

            # Set all step sizes
            for widget in self.num_widgets:
                widget.setSingleStep(step_size)

            self.step_size.valueChanged.connect(self._update_step_sizes)

        # Handle case where step size was not in the GUI
        except AttributeError:
            self.num_widgets = None

    def _update_step_sizes(self):
        """ Updates all step sizes of QDoubleSpinBox widgets to current value of step_size widget """

        # Get current step size
        step_size = self.step_size.value()

        # Set all step sizes
        for widget in self.num_widgets:
            widget.setSingleStep(step_size)

    def _run_gui(self):
        """Runs the GUI. Displays the main window"""

        self.show()

    def _assign_plot(self, plot_widget, plot_label, legend_widget):
        """ Assigns a plot to a particular plot widget

        :param plot_widget: (str) name of the plot widget to use in the GUI window
        :param plot_label: (str) label to use for future referencing of the plot widget from the self.plots dictionary
        :param legend_widget: (str) name of the GraphicsView widget to use in the GUI window for this plot legend
        """

        # Assign plot
        self.plots[plot_label] = Plot(self, plot_widget, legend_widget)

        # Set title
        self.plots[plot_label].widget.setTitle(plot_label)

    def _clear_plot(self, plot_widget):
        """ Clears a plot and removes it from the self.plots attribute

        :param plot_widget: (str) name of the plot widget (instance of PYQTgraph) to clear
        """

        # Identify the plot widget
        widget_to_remove = getattr(self, plot_widget)

        # Find the relevant widget
        plot_to_delete = None
        for plot_label, plot in self.plots.items():
            if plot.widget is widget_to_remove:

                # Remove all curves
                curves_to_remove = []
                for curve_label in plot.curves:
                    curves_to_remove.append(curve_label)
                for curve_to_remove in curves_to_remove:
                    plot.remove_curve(curve_to_remove)

                # Remove plot from self.plots
                plot_to_delete = plot_label
        if plot_to_delete is not None:
            del self.plots[plot_to_delete]

    def _assign_curve(self, plot_label, curve_label, error=False):
        """ Assigns a curve to a plot

        :param plot_label: (str) label of the plot to assign
        :param curve_label: (str) label of curve to use for indexing in the self.plots[plot_label].curves dictionary
        :param error: (bool, optional) whether or not to use error bars
        """
        self.plots[plot_label].add_curve(curve_label, error)

    def _remove_curve(self, plot_label, curve_label):
        """ Removes a curve from a plot

        :param plot_label: (str) label of plot holding curve
        :param curve_label: (str) label of curve to remove
        """
        self.plots[plot_label].remove_curve(curve_label)

    def _assign_scalar(self, scalar_widget, scalar_label):
        """ Assigns scalar widget display in the GUI

        :param scalar_widget: (str) name of the scalar widget (e.g. QLCDNumber) in the GUI
        :param scalar_label: (str) label of the scalar widget
        """
        self.scalars[scalar_label] = Scalar(self, scalar_widget)

    def _assign_label(self, label_widget, label_label):
        """ Instantiates label object and assigns it to reference string

        :param label_widget: (str) name of the label widget (e.g. QLabel) in the GUI
        :param label_label: (str) reference string for the label
        """
        self.labels[label_label] = Label(self, label_widget)

    def _assign_event_button(self, event_widget, event_label):
        """ Assigns physical event button

        :param event_widget: (str) name of physical button widget on GUI
        :param event_label: (str) key name for reference to button
        """

        self.event_buttons[event_label] = EventButton(
            gui=self,
            event_widget=event_widget
        )

    def _assign_container(self, container_widget, container_label):
        """ Assigns physical ;ost

        :param container_widget: (str) name of physical container widget on GUI
        :param container_label: (str) key name for reference to the container
        """

        self.containers[container_label] = Container(
            gui=self,
            widget=container_widget
        )


class ParameterPopup(QtWidgets.QWidget):
    """ Widget class of to add parameter prompting popup"""
    parameters = QtCore.pyqtSignal(dict)

    def __init__(self, **params):
        """ Instantiates window

        :param params: (dict) with keys giving parameter
            name and value giving parameter type
        """

        QtWidgets.QWidget.__init__(self)

        # Create layout
        self.base_layout = QtWidgets.QVBoxLayout()
        self.setStyleSheet('background-color: rgb(0, 0, 0);'
                           'font: 25 12pt "Calibri Light";'
                           'color: rgb(255, 255, 255);')
        self.setWindowTitle('Parameter Configurator')
        self.setMinimumWidth(300)
        self.setLayout(self.base_layout)
        self.params = {}

        # Add labels and widgets to layout
        for param_name, param_type in params.items():
            layout = QtWidgets.QHBoxLayout()
            layout.addWidget(QtWidgets.QLabel(param_name))
            if param_type is int:
                self.params[param_name] = QtWidgets.QSpinBox()
                self.params[param_name].setMaximum(100000000)
            elif param_type is float:
                self.params[param_name] = QtWidgets.QDoubleSpinBox()
                self.params[param_name].setMaximum(100000000)
            else:
                self.params[param_name] = QtWidgets.QLabel()
            layout.addWidget(self.params[param_name])
            self.base_layout.addLayout(layout)

        # Add button to configure
        self.configure_button = QtWidgets.QPushButton(text='Configure Parameters')
        self.configure_button.setStyleSheet('background-color: rgb(170, 170, 255);')
        self.base_layout.addWidget(self.configure_button)
        self.configure_button.clicked.connect(self.return_params)
        self.show()

    def return_params(self):
        """ Returns all parameter values and closes """

        ret = {}
        for param_name, widget in self.params.items():
            try:
                ret[param_name] = widget.value()
            except AttributeError:
                ret[param_name] = widget.text()
        self.parameters.emit(ret)
        self.close()


class Plot:
    """ Class for plot widgets inside of a Window

    See also Curve class for specific curves, multiple of which can be assigned within a plot
    """

    # Semi-arbitrary list of colors to cycle through for plot data
    COLOR_LIST = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',
                   '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
                   '#000075', '#808080']

    def __init__(self, gui, plot_widget, legend_widget):
        """ Instantiates plot object for a plot inside of the GUI window

        See technical details about the legend implementation in the _set_legend() method

        :param gui: (Window) instance of the GUI window
        :param plot_widget: (str) name of the plot widget
        :param legend_widget: (str) name of the legend widget
        """

        # Assign the actual widget object, which is an instance of pyqtgraph.PlotWidget
        self.gui = gui
        self.widget = getattr(self.gui, plot_widget)

        self.curves = {}  # Holds all curves for this plot with associated curve label key
        self.legend = None  # Holds legendItem instance for plot legend

        # Set up legend
        self._set_legend(legend_widget=legend_widget)

    def add_curve(self, curve_label, error=False):
        """ Adds a curve to the plot

        TODO (if someone wants...): implement custom curve property override (e.g. custom color, line style, etc)

        :param curve_label: (str) curve label key to attach to this curve for future reference + naming purposes
        :param error: (bool, optional) whether or not to use error bars
        """

        # Add a new curve to self.curves dictionary for this plot
        self.curves[curve_label] = Curve(
            self.widget,
            pen=pg.mkPen(color=self.COLOR_LIST[len(self.curves)]),  # Instantiate a Pen for curve properties
            error=error
        )

        # Configure legend
        self._add_to_legend(curve_label)

    def remove_curve(self, curve_label):
        """ Removes a curve from the plot

        :param curve_label: (str) name of curve to remove
        """

        # Remove from legend
        self._remove_from_legend(curve_label)

        # Remove from plot
        self.widget.removeItem(self.curves[curve_label].widget)

        # Remove from dictionary of curves
        del self.curves[curve_label]

    def update_output(self):
        """ Updates plot output to latest data"""

        for curve in self.curves.values():

            # Set data without error bars
            curve.widget.setData(
                curve.data
            )

            if curve.error_data is not None:
                curve.error.setData(
                    x=np.arange(len(curve.data)),
                    y=curve.data,
                    height=2*curve.error_data
                )

    # Technical methods

    def _set_legend(self, legend_widget):
        """ Sets the legend for a plot.

        Should be invoked once at the beginning when a plot is initialized. Requires a GraphicsView instance in order to
        serve as a container for the legend. This can be done by dragging a QGraphicsView object into the desired shape
        and location in the GUI, and promoting to a GraphicsView object with the pyqtgraph header. The legend is
        configured to sit in the top left corner of the box.

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
        """ Adds a curve to the legend

        :param curve_label: (str) key label of curve in self.curves dictionary to add to legend
        """

        # Add some space to the legend to prevent overlapping
        self.legend.addItem(self.curves[curve_label].widget, ' - '+curve_label)

    def _remove_from_legend(self, curve_label):
        """ Removes a curve from the legend

        :param curve_label: (str) label of curve to remove from legend
        """
        self.legend.removeItem(' - '+curve_label)


class Curve:
    """ Class for individual curves within a Plot """

    def __init__(self, plot_widget, pen=None, error=False):
        """ Instantiates a curve inside of a plot_widget

        :param plot_widget: (pg.PlotItem) instance of plot widget to add curve to
        :param pen: (pg.Pen) pen to use to draw curve
        :param error: (bool, optional) whether or not to add error bars to this plot
        """

        # Instantiate error bar plot
        self.widget = plot_widget.plot(pen=pen)

        if error:
            self.error = pg.ErrorBarItem(
                x=np.array([]),
                y=np.array([]),
                pen=pen
            )
            plot_widget.addItem(self.error)
            self.error_data = np.array([])

        # Instantiate new curve in the plot without error bars
        else:
            self.widget = plot_widget.plot(pen=pen)
            self.error = None
            self.error_data = None

        self.data = np.array([])

    def set_curve_data(self, data, error=None):
        """ Stores data to a new curve

        :param data: (np.array) either a 1D (only y-axis) or 2D (x-axis, y-axis) numpy array
        :param error: (np.array, optional) 1D array for error bars (standard deviation)
        """

        self.data = data

        if self.error_data is not None:
            self.error_data = error


class Scalar:
    """ A scalar display object (e.g. a number or boolean)

    Currently supports any instance of QAbstractButton (booleans such as pushbuttons and checkboxes), QAbstractSpinbox
    (numerical displays/inputs) and QLCDNumber (swanky digital number displays)

    Also supports two-way functionality (not just data display). See module doctstring for details
    """

    def __init__(self, gui, scalar_widget):
        """ Initializes the scalar object

        By default, activates the widget so it can be updated via an external script and is effectively blocked from
        user input. Call the deactivate() method in order to deactivate and enable GUI input.

        :param gui: (Window) instance of the GUI window class containing the number widget
        :param scalar_widget: (str) name of the widget for reference
        """

        self.data = None
        self._use_data = True  # Whether or not the widget is active

        # Get actual widget instance
        self.widget = getattr(gui, scalar_widget)

    def set_data(self, data):
        """ Sets the value of the scalar internally

        :param data: number to set to
        """
        self.data = data

    def update_output(self):
        """ Updates the physical output of the scalar widget

        Checks if the widget is active, in which case it sets the output to self.data. If not, it just maintains the
        current output of the GUI.
        """

        # Check if active
        if self._use_data:

            # Set the state, checking first whether it is a boolean display or not
            if isinstance(self.data, bool):
                # Check if the script has updated and implement
                self.widget.setChecked(self.data)

            # Handle numerical widgets
            elif self.data is not None:
                # Now if it is simply a QLCDButton, it should have the display method
                try:
                    if self.widget.value() != self.data:
                        display_str = '%.6f' % self.data
                        self.widget.display(display_str)

                # In case client disconnects
                except EOFError:
                    pass

                # If it is an input numerical display, update!
                except AttributeError:
                    try:
                        self.widget.setValue(self.data)
                    # In case client disconnects

                    except EOFError:
                        pass

                    # In case it is some other funky widget we haven't accounted for
                    # Future addition to scalar implementation can go inside here
                    except AttributeError:
                        pass

    def get_data(self):
        """ Gets the current data from the GUI widget

        :return: current data (either a bool or a double)
        """

        # First try the boolean implementation
        try:
            data = self.widget.isChecked()

        # Next try the numerical (works for QLCDNumber and QAbstractSpinBox
        except AttributeError:
            data = self.widget.value()
        return data

    def activate(self):
        """ Tells a scalar to use its data, locking GUI editing and updating from the script"""
        self._use_data = True

    def deactivate(self):
        """ Tells a scalar not to use its data, enables free GUI editing"""
        self._use_data = False


class Label:
    """ A text label display object. Currently supports QLabel"""

    def __init__(self, gui, label_widget):
        """ Constructor for label object

        :param gui: (Window) instance of GUI window class containing the label object
        :param label_widget: (str) name of the widget for reference
        """

        self.text = None
        self.widget = getattr(gui, label_widget)

    def set_label(self, label_text=''):
        """ Sets label text

        :param label_text: (str, optional) text string to set the label to
        """

        self.text = label_text
        self.widget.setText(label_text)

    def get_label(self):
        """ Returns label text """

        try:

            # Ordinary labels
            return self.widget.text()
        except AttributeError:

            # Fancy labels
            return self.widget.toPlainText()


class EventButton:
    """ Class for event pushbuttons to be tied to some script functions externally """

    def __init__(self, gui, event_widget):
        """ Instantiates event button """

        self.was_pushed = False  # Keeps track of whether the button has been pushed
        self.was_released = False
        self.widget = getattr(gui, event_widget)  # Get physical widget instance

        self.disabled = False  # Check if button is disabled

        # Connect event to flag raising
        self.widget.pressed.connect(self.button_pressed)
        self.widget.released.connect(self.button_released)

    def button_pressed(self):
        """ Raises flag when button is pushed """

        self.was_pushed = True

    def button_released(self):
        """ Raises flag when button is released """

        self.was_released = True

    def reset_button(self):
        """ Resets pushed state to False """

        self.was_pushed = False
        self.was_released = False

    def change_background_color(self, color):
        """ Changes background_color of button"""

        self.widget.setStyleSheet(f"background-color: {color}")

    def set_text(self, text):
        """ Sets button text"""

        self.widget.setText(text)

    def get_state(self):
        """ Returns whether or not the button has been pressed and resets button state

        :return: bool self._was_pushed
        """

        result = copy.deepcopy(self.was_pushed)
        self.reset_button()
        return result

    def get_release_state(self):
        """ Returns whether or not the button has been released and resets this flag

        :return: bool self._was_released
        """

        result = copy.deepcopy(self.was_released)
        self.was_released = False
        if result or not self.widget.isDown():
            result = True
        return result

    def is_pressed(self):
        """ Checks whether or not the physical button is currently pressed

        :return: (bool) whether or not the button is down
        """

        return self.widget.isDown()


class Container:
    """ Class for generic containers with elements added within

    Idea being that all that needs to be referenced is the top level
    and methods here can be invoked to get information about containing elements

    Partially supported widgets: QListWidget, QComboBox
    Read method docstrings for details
    """

    def __init__(self, gui, widget):
        """ Instantiates event button """

        self.widget = getattr(gui, widget)  # Get physical widget instance

    def get_items(self):
        """ Returns all QListWidget items and tooltips as a dictionary """

        item_info = {}
        for index in range(self.widget.count()):

            # Get the current item and store its name and tooltip text
            current_item = self.widget.item(index)
            item_info[current_item.text()] = current_item.toolTip()

        return item_info

    def get_current_text(self):
        """ Returns current text of a QComboBox"""

        return self.widget.currentText()

    def get_current_index(self):
        """ Returns current index of a QComboBox"""

        return self.widget.currentIndex()

    def set_item_index(self, index):
        """ Sets the current index of a QComboBox

        :param index: (int) index to set to
        """

        self.widget.setCurrentIndex(index)
