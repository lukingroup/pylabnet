""" Runs the WlmMonitor script

Instantiates clients that connect to AO, Wavemeter, and GUI servers. Runs an update server.
Continuously runs wavemeter monitoring script (see pylabnet/scripts/wlm_monitor.py for details)
"""

from pylabnet.utils.logging.logger import LogClient
from pylabnet.hardware.wavemeter import high_finesse_ws7
from pylabnet.hardware.ni_daqs import nidaqmx_card
from pylabnet.gui.pyqt import external_gui
from pylabnet.scripts.wlm_monitor import WlmMonitor, Service
from pylabnet.core.generic_server import GenericServer


def main():

    # Connect to servers
    try:
        wavemeter_client = high_finesse_ws7.Client(host='localhost', port=5678)
        wavemeter_client.connect()
    except ConnectionRefusedError:
        raise Exception('Cannot connect to wavemeter server')
    try:
        ao_client = nidaqmx_card.Client(host='localhost', port=9912)
        ao_client.connect()
    except ConnectionRefusedError:
        raise Exception('Cannot connect to NI DAQmx server')
    try:
        gui_client = external_gui.Client(host='localhost', port=9)
        gui_client.connect()
    except ConnectionRefusedError:
        raise Exception('Cannot connect to GUI server')

    # Instantiatelogger for gui_handler error output
    log_client_wlm_monitor = LogClient(
        host='localhost',
        port=1234,
        module_tag='Wavemeter GUI control'
    )

    # Instantiate Monitor script
    wlm_monitor = WlmMonitor(
        wlm_client=wavemeter_client,
        gui_client=gui_client,
        ao_clients={'cDAQ1': ao_client},
        logger_client=log_client_wlm_monitor
    )

    # Instantiate pause+update service & connect to logger
    log_client_update = LogClient(
        host='localhost',
        port=1234,
        module_tag='Pause & Update'
    )
    update_service = Service()
    update_service.assign_module(module=wlm_monitor)
    update_service.assign_logger(logger=log_client_update)
    update_server = GenericServer(
        host='localhost',
        port=897,
        service=update_service
    )
    update_server.start()

    # Set parameters
    # Can use these as default parameters for loading up the monitor initially. New parameters can be input afterwards
    # using an update client
    wlm_monitor.set_parameters(
        channel_params=[
            dict(channel=1, name="Velocity", AO=dict(client='cDAQ1', channel='ao0'),
                 PID=dict(p=0.15, i=0.01, d=0), memory=100, voltage_monitor=True)
        ]
    )

    # Initialize channels to GUI
    wlm_monitor.initialize_channels()

    # Run continuously
    # Note that the actual operation inside run() can be paused using the update server
    while True:

        # Make sure the WlmMonitor is not paused, otherwise run it
        if not wlm_monitor.is_paused:
            wlm_monitor.run()


if __name__ == '__main__':
    main()
