from pylabnet.network.client_server.keithley_2400 import Service, Client
from pylabnet.utils.helper_methods import load_device_config, get_ip
import pylabnet.hardware.keithley_2400.keithley_2400 as k2400
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """Connect to Keithley 2400 SourceMeter and instantiate server.
    Optional config entries:
        reset_on_init: bool, default True
        timeout_ms: int, default 10000
    """
    logger = kwargs["logger"]
    config = kwargs['config']
    config = load_device_config("keithley_2400", config, logger=logger)

    smu = k2400.Driver(
        gpib_address=config["device_id"],
        logger=logger,
    )

    smu_service = Service()
    smu_service.assign_module(module=smu)
    smu_service.assign_logger(logger=logger)

    smu_server = GenericServer(
        service=smu_service,
        host=get_ip(),
        port=kwargs["port"],
    )
    smu_server.start()
