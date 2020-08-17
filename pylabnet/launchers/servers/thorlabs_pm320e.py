import socket
import time
import pyvisa

from pylabnet.hardware.power_meter.thorlabs_pm320e import Driver
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.network.client_server.thorlabs_pm320e import Service, Client
from pylabnet.utils.helper_methods import show_console, hide_console, load_config

def launch(**kwargs):
    """ Connects to PM320E and instantiates server

    :param kwargs: (dict) containing relevant kwargs
        :logger: instance of LogClient for logging purposes
        :port: (int) port number for the Cnt Monitor server
    """

    try:
        settings = load_config(
            kwargs['config'],
            logger=kwargs['logger']
        )
    except KeyError:
        kwargs['logger'].warn('No config file was provided')

    try:
        pm = Driver(
            logger=kwargs['logger'],
            gpib_address=settings['GPIB'],
        )

    # Handle error of wrong GPIB address by allowing user to select
    # NOTE: this will fail if used from the main script launcher, since script client
    # will automatically try to connect (even though server isn't launched)
    #
    # TLDR: if you want to use launch-control, please fill in GPIB variable with
    # the correct resource string
    except:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        show_console()
        print('Current resources:')
        for index, resource in enumerate(resources):
            print(f'{index}: {resource}')
        address = int(input('\nSelect the index of the target resource: '))
        try:
            pm = Driver(
                logger=kwargs['logger'],
                gpib_address=resources[address]
            )
        except:
            kwargs['logger'].error(f'Failed to connect to {resources[address]} properly.')
        hide_console()

    pm_service = Service()
    pm_service.assign_module(module=pm)
    pm_service.assign_logger(logger=kwargs['logger'])
    pm_server = GenericServer(
        service=pm_service,
        host=socket.gethostbyname(socket.gethostname()),
        port=kwargs['port']
    )
    pm_server.start()
