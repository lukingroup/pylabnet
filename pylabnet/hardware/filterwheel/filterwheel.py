# -*- coding: utf-8 -*-


"""
This file contains the pylabnet Hardware module class for Thorlabs FW102c Filterwheel.

Is is essentially a wrapper for the class  FW102C in fw102.py writen by Gilles Simond

"""

from pylabnet.hardware.filterwheel.fw102c import FW102C
from pylabnet.utils.logging.logger import LogHandler




class FW102CFilterWheel():

    def __init__(self, port_name, device_name, filters, logger=None):
        """Instantiate Harware class for FW102c Filterwheel by instanciating a FW102C class

        :device_name:Readable name of device, e.g. 'Collection Filters'
        :port_name:Port name over which Filter wheel is connect via USB
        :filters: A dictionary where the keys are the numbered filter positions and the values are strings describing the filter, e.g. '4 ND'
        """

        # Instanciate log
        self.log = LogHandler(logger=logger)

        # Retrieve name and filter options
        self.device_name = device_name
        self.filters = filters

        # Instanciate FW102C 
        self.filterwheel = FW102C(port=port_name, logger=self.log)

        if not self.filterwheel.isOpen:
            self.log.error("Filterwheel {} connection failed".format(self.device_name))
        else:
            self.log.info("Filterwheel {} connection successfully".format(self.device_name))

    def get_pos(self):
        """Returns current position of filterwheel

        """
        return self.filterwheel.query('pos?')
        

    def change_filter(self, new_pos):
        """Update filter wheel position

        :new_pos:Target filter wheel position 1-6 or 1-12
        """

        # Update Position
        self.filterwheel.command('pos={}'.format(new_pos))

        # Check if update was successful
        if int(self.get_pos()) == int(new_pos):
            self.log.info("Filterwheel {device_name} changed to position {position} ({filter})".format(
                device_name = self.device_name,
                position = new_pos,
                filter = self.filters.get('{}'.format(new_pos)))
            )
        else:
            self.log.info("Filterwheel {device_name} changing to position failed".format( device_name = self.device_name))



  
   


        