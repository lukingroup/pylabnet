""" Qudi module to make confocal refocus network-visible
"""


# Imports of qudi's modules
from core.module import Base, ConfigOption, Connector
from logic.generic_logic import GenericLogic

# Import of pylabnet's modules
# (make sure that pylabnet location is in qudi's sys.path)
from pylabnet.core.generic_server import GenericServer
from pylabnet.core.service_base import ServiceBase


class RefocusService(ServiceBase):

    _optimizer_logic = None
    _scanning_logic = None

    def set_logic(self, optim_logic, scan_logic):
        self._optimizer_logic = optim_logic
        self._scanning_logic = scan_logic

    def exposed_refocus(self):
        crosshair_pos = self._scanning_logic.get_position()
        self._optimizer_logic.start_refocus(crosshair_pos, 'confocalgui')
        return 0


class RefocusServer(GenericLogic):
    """
    This class should be instantiated as Qudi Logic module
    to allow starting refocus through a client

    Config:

    logic:
        refocus_server:
            module.Class: 'refocus_server.RefocusServer'
            host: 'localhost'
            port: 1234
            connect:
                optimizer_logic: 'optimizerlogic'
                scanner_logic: 'scannerlogic'
    """

    _modclass = 'RefocusServer'
    _modtype = 'logic'

    _host = ConfigOption(name='host', missing='error')
    _port = ConfigOption(name='port', missing='error')

    optimizer_logic = Connector(interface='DoesNotMatter')
    scanner_logic = Connector(interface='DoesNotMatter')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._service = RefocusService()
        self._service.set_logic(
            optim_logic=self.optimizer_logic(),
            scan_logic=self.scanner_logic()
        )

        self._server = GenericServer(
            host=self._host,
            port=self._port,
            service=self._service
        )

        self._server.start()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

