from pylabnet.utils.helper_methods import load_config
from pylabnet.utils.logging.logger import LogHandler
import asyncio
from kasa import Discover



class Device():

    def __init__(self, plug_location, logger=None):
        """ Initiilzes connection to a Smart plug.

        :location: Location of Smart plug as defined in smart plug config dict.
        """

        # Instantiate log.
        self.log = LogHandler(logger=logger)

        self.plug_location = plug_location

        self.plug_config = load_config('smart_plug_config')

        self.plug_type, self.dev_id = self.get_device_info(plug_location)

        # Discover Smart Plugs
        found_devices = asyncio.run(Discover.discover())
        found_device_ids = [dev.alias for dev in found_devices.values()]

        if not self.dev_id in found_device_ids:
            self.log.error(f"Smart Plug at location '{self.plug_location}' with device id '{self.dev_id}' not found. Connected devices are: {found_device_ids}")
        else:
            self.log.info(f"Smart Plug at location '{self.plug_location}' with device id '{self.dev_id}' discovered.")


    def get_device_info(self, plug_location):

        dev_id, current_plug_type = None, None

        for plug_type in self.plug_config.keys():
            for location_dict in self.plug_config[plug_type]:
                if location_dict['location'] == plug_location:

                    dev_id = location_dict['dev_id']
                    current_plug_type = plug_type
                    break

        if dev_id is not None:
            return current_plug_type, dev_id
        else:
            self.log.error(f"Could not find plug location {dev_id} in smart_plug_config.json.")




def main():
    from pylabnet.utils.logging.logger import LogClient

    # Instantiate LogClient.
    logger = LogClient(
        host='192.168.50.100',
        port=47352,
        module_tag=f'smart_plug'
    )

    sp = Device(
        plug_location="Powermeter Front",
        logger=logger
    )


if __name__ ==  "__main__":
    main()