from pylabnet.utils.helper_methods import load_config
from pylabnet.utils.logging.logger import LogHandler
import asyncio
from kasa import Discover


class Driver():

    def __init__(self, channels, logger=None):
        """ Initializes connection to all TP Kasa smart plugs in the network.

        :channels: list of channels accessaable via this smart plug interface
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.channels = channels

        # Discover smart plugs.
        self.found_devices = asyncio.run(Discover.discover())

        # Store aliases of found devices.
        self.found_device_aliases = [dev.alias for dev in self.found_devices.values()]

        self.log.info(f"Discovered {len(self.found_device_aliases)} smart plugs.")

    def retrieve_device(self, channel_id):
        """ Returns kasa.SmartPlug object corresponding to a specific plug.

        The plugs are identified with channel_ids, which usually correspond to human readable names of the plug location,
            e.g. "Lights Kitchen". The config file then matches the channel_ids to the plug aliases,
            as they have been defined using the Kasa app.
        :channel_id: (str) Human readable device ID.
        """
        _, alias = self.get_device_info(channel_id)

        if not alias in self.found_device_aliases:
            self.log.error(f"Smart Plug at location '{channel_id}' with plug alias '{alias}' not found. Connected devices are: {self.found_device_aliases}")
        else:
            self.log.info(f"Smart Plug at location '{channel_id}' with plug alias '{alias}' discovered.")

        device = [dev for dev in self.found_devices.values() if dev.alias == alias][0]

        # Run update.
        asyncio.run(device.update())

        return device

    def turn_on(self, channel_id):
        """Turn plug on.

        :channel_id: (str) Human readable device ID.
        """

        device = self.retrieve_device(channel_id)
        asyncio.run(device.turn_on())
        self.log.info(f"Smart Plug at location '{channel_id}' turned on.")

    def turn_off(self, channel_id):
        """Turn plug off.

        :channel_id: (str) Human readable device ID.
        """

        device = self.retrieve_device(channel_id)
        asyncio.run(device.turn_off())
        self.log.info(f"Smart Plug at location  '{channel_id}' turned off.")

    def is_on(self, channel_id):
        """ Returns True is plug is on.

        :channel_id: (str) Human readable channel ID.
        """
        device = self.retrieve_device(channel_id)
        return device.is_on

    def get_device_info(self, channel_id):
        """ Read config dict and find alias matching to channel_id.

        :channel_id: (str) Human readable device ID.
        """

        alias, current_plug_type = None, None

        for location_dict in self.channels:
            if location_dict['channel_id'] == channel_id:
                alias = location_dict['alias']
                break

        if alias is not None:
            return current_plug_type, alias
        else:
            self.log.error(f"Could not find plug location {channel_id} in smart_plug_config.json.")
