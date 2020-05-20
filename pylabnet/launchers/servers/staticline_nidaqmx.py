''' Configures a Staticline instance to use a NIDaqmx output'''

from pylabnet.hardware.ni_daqs import nidaqmx_card
from pylabnet.network.client_server.nidaqmx_card import Service
from pylabnet.network.core.generic_server import GenericServer


def launch(**kwargs):
    """ Connects to a NI DAQ as staticline

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    import pylabnet.hardware.ni_daqs.nidaqmx_card as nidaqmx

    device_name = 'cDAQ1Mod1'
    daq = nidaqmx.Driver(device_name=device_name, logger=kwargs['logger'])

    test_staticline = nidaqmx_card.Driver(
        name='Test staticline',
        logger=kwargs['logger'],
        hardware_module=daq,
        ao_output='ao2',

        down_voltage=0,
        up_voltage=3.3,
    )

    # Instantiate Server
    # Staticline server
    staticline_service = Service()
    staticline_service.assign_module(module=test_staticline)
    staticline_service.assign_logger(logger=kwargs['logger'])
    staticline_service_server = GenericServer(
        service=staticline_service,
        host='localhost',
        port=kwargs['port']
    )

    staticline_service_server.start()
