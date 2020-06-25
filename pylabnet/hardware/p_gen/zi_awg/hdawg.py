""" Driver for Zurich Instruments HDAWG """

import zhinst.ziPython as zi


class Driver:

    def __init__(self, dev='DEV8040'):

        # Start ZI DAQ server
        self._discovery = zi.ziDiscovery()
        self.device_id = self._discovery.find(dev)
        device_props = self._discovery.get(self.device_id)
