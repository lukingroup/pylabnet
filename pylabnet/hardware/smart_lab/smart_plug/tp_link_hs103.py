from pylabnet.utils.helper_methods import load_config
from pylabnet.utils.logging.logger import LogHandler
import asyncio
from kasa import Discover


class Driver():

    def __init__(self, logger=None):
        """ Initializes connection to all TP Kasa smart plugs in the network.

        :device_id: Location of smart plug as defined in smart plug config dict (e.g. "Powermeter Front Smart Plug").
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.plug_config = load_config('smart_plug_config')

        # Discover smart plugs.
        self.found_devices = asyncio.run(Discover.discover())

        # Store aliases of found devices.
        self.found_device_aliases = [dev.alias for dev in self.found_devices.values()]

        self.log.info(f"Discovered {len(self.found_device_aliases)} smart plugs.")

    def retrieve_device(self, device_id):
        """ Returns kasa.SmartPlug object corresponding to a specific plug.

        The plugs are identified with device_ids, which usually correspond to human readable names of the plug location,
            e.g. "Lights Kitchen". The config file smart_plug_config.json then matches the device_ids to the plug aliases,
            as they have been defined using the Kasa app.
        :device_id: (str) Human readable device ID.
        """
        _, alias = self.get_device_info(device_id)

        if not alias in self.found_device_aliases:
            self.log.error(f"Smart Plug at location '{device_id}' with plug alias '{alias}' not found. Connected devices are: {self.found_device_aliases}")
        else:
            self.log.info(f"Smart Plug at location '{device_id}' with plug alias '{alias}' discovered.")

        device = [dev for dev in self.found_devices.values() if dev.alias == alias][0]

        # Run update.
        asyncio.run(device.update())

        return device

    def turn_on(self, device_id):
        """Turn plug on.

        :device_id: (str) Human readable device ID.
        """

        device = self.retrieve_device(device_id)
        asyncio.run(device.turn_on())
        self.log.info(f"Smart Plug at location '{device_id}' turned on.")

    def turn_off(self, device_id):
        """Turn plug off.

        :device_id: (str) Human readable device ID.
        """

        device = self.retrieve_device(device_id)
        asyncio.run(device.turn_off())
        self.log.info(f"Smart Plug at location  '{device_id}' turned off.")

    def is_on(self, device_id):
        """ Returns True is plug is on.

        :device_id: (str) Human readable device ID.
        """
        device = self.retrieve_device(device_id)
        return device.is_on

    def get_device_info(self, device_id):
        """ Read config dict and find alias matching to device_id.

        :device_id: (str) Human readable device ID.
        """

        alias, current_plug_type = None, None

        for plug_type in self.plug_config.keys():
            for location_dict in self.plug_config[plug_type]:
                if location_dict['device_id'] == device_id:

                    alias = location_dict['alias']
                    current_plug_type = plug_type
                    break

        if alias is not None:
            return current_plug_type, alias
        else:
            self.log.error(f"Could not find plug location {device_id} in smart_plug_config.json.")