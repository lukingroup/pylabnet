""" Implements connection and server launching to a quantum machine opx+ """


from pylabnet.hardware.awg.quantum_machine import Driver
from pylabnet.network.client_server.quantum_machine import Service, Client
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.utils.helper_methods import get_ip, load_device_config

def launch(**kwargs):
    """ Connects to Quantum Machine OPX+ and launches server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
    """
    qm_logger = kwargs['logger']
    config = load_device_config('quantum_machine', kwargs['config'], qm_logger)

    # Instantiate driver
    qm_driver = Driver(
        device_name=config['device_id'],
        host=config['host'],
        logger=qm_logger
    )

    # Instantiate server
    qm_service = Service()
    qm_service.assign_module(module=qm_driver)
    qm_service.assign_logger(logger=qm_logger)
    qm_server = GenericServer(
        service=qm_service,
        host=get_ip(),
        port=kwargs['port']
    )

    qm_server.start()