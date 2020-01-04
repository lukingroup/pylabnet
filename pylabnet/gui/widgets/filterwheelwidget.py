# -*- coding: utf-8 -*-

"""
This file contains wrappers for Jupyter Notebook Widgets used for controlling the SC20 Shutter
"""

import ipywidgets as widgets


class FilterwheelToogle:
    """ This Class implements a toggle change the filter of a Thorlabs FW102C Filterwheel
    """

    def __init__(self, filterwheel_client):

        # retrieve shutter name
        self.name = filterwheel_client.get_name()

        # retrieve shutter client
        self.filterwheel_client = filterwheel_client

        # retrieve filterwheel dictionary
        self.filters = filterwheel_client.get_filter_dict()

        # retrieve filter names for dropdown selection
        dropdown_options = [(self.filters[i], int(i)) for i in list(self.filters.keys())]

        # Retrieve initial position of filterwheel
        init_pos = filterwheel_client.get_pos()

        # Dropdown Widget
        self.dropdown_raw = widgets.Dropdown(
            options=dropdown_options,
            value=int(init_pos),
        )

        # Add label to toogle
        self.dropdown = widgets.HBox(
            [
                widgets.Label("Filterwheel {name}".format(name=self.name)),
                self.dropdown_raw
            ]
        )

        self.output = widgets.Output()

        # Display Toogle
        display(self.dropdown, self.output)

    def on_value_change(self, change, protect_shutter_client=None):
        with self.output:
            return self.filterwheel_client.change_filter(
                int(change['new']),
                protect_shutter_client
            )
