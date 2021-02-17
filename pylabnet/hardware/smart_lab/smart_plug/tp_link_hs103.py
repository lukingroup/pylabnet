from pylabnet.utils.helper_methods import load_config
from pylabnet.utils.logging.logger import LogHandler
import asyncio
from kasa import Discover


class Driver():

    def __init__(self, device_id, logger=None):
        """ Initializes connection to a TP Link HS103 Kasa Smart Plug.

        :device_id: Location of smart plug as defined in smart plug config dict (e.g. "Powermeter Front Smart Plug").
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        # Store smart plug location and retrieve device id.
        self.device_id = device_id
        self.plug_config = load_config('smart_plug_config')
        self.plug_type, self.alias = self.get_device_info()

        # Discover Smart Plugs.
        found_devices = asyncio.run(Discover.discover())
        found_device_aliases = [dev.alias for dev in found_devices.values()]

        if not self.alias in found_device_aliases:
            self.log.error(f"Smart Plug at location '{self.device_id}' with plug alias '{self.alias}' not found. Connected devices are: {found_device_aliases}")
        else:
            self.log.info(f"Smart Plug at location '{self.device_id}' with plug alias '{self.alias}' discovered.")

        self.plug = [dev for dev in found_devices.values() if dev.alias == self.alias][0]

        # Run update.
        asyncio.run(self.plug.update())

    def turn_on(self):
        """Turn switch on."""
        asyncio.run(self.plug.turn_on())
        self.log.info(f"Smart Plug at location '{self.device_id}' turned on.")

    def turn_off(self):
        """Turn switch off."""
        asyncio.run(self.plug.turn_off())
        self.log.info(f"Smart Plug at location  '{self.device_id}' turned off.")

    def is_on(self):
        """ Returns True is plug is on."""
        return self.plug.is_on

    def get_device_info(self):
        """ Read config dict and find device_id matching to plug_location."""

        alias, current_plug_type = None, None

        for plug_type in self.plug_config.keys():
            for location_dict in self.plug_config[plug_type]:
                if location_dict['device_id'] == self.device_id:

                    alias = location_dict['alias']
                    current_plug_type = plug_type
                    break

        if alias is not None:
            return current_plug_type, alias
        else:
            self.log.error(f"Could not find plug location {self.device_id} in smart_plug_config.json.")



def main():

    from pylabnet.utils.logging.logger import LogClient


    # Instantiate LogClient.
    logger = LogClient(
        host='192.168.50.100',
        port=47352,
        module_tag='Smart_plug'
    )

    sp = Driver(
        device_id="Powermeter Front Smart Plug",
        logger=logger
    )

if __name__ == "__main__":
    main()