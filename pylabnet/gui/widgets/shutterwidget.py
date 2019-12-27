# -*- coding: utf-8 -*-


"""
This file contains wrappers for Jupyter Notebook Widgets used for controling the SC20 Shutter

"""

import ipywidgets as widgets


class Shuttertoogle():
    """
    This Class implements a toggle switch to open and close the SC20 Shutter
    """

    def __init__(self, shutter_client):

            # retrieve shutter name
            self.name = shutter_client.get_name()

            # retrieve shutter client
            self.shutter_client = shutter_client


            # The toogle button
            self.toogle_raw = widgets.ToggleButtons(
                options=['Closed', 'Open'],
                disabled=False,
                button_style='', # 'success', 'info', 'warning', 'danger' or ''
                tooltips=['Close Shutter', 'Open Shutter'],
                layout=widgets.Layout(
                    width='50%', 
                    height='80px'
                )
            )

            # Add label to toogle
            self.toogle = widgets.HBox(
                [widgets.Label('Shutter {}:'.format(self.name)), 
                self.toogle_raw]
                )


            self.output = widgets.Output()

            #Display Toogle
            display(self.toogle, self.output)

    def on_value_change(self, change):
            with self.output:
                if change['new'] == 'Open':
                    return self.shutter_client.open()
                elif change['new'] == 'Closed':
                    return self.shutter_client.close()
