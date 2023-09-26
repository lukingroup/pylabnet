""" Set of tools to stop continuously running script from a different process
via RPyC link.

Steps:
- the script class should have public method pause(),
  which will be called by client through RPyC link
- once the script is instantiated, assign it as the module to
  PauseService instance:
      pause_service_instance.assign_module(script_instance)
- instantiate PauseClient in a different process
- call of PauseClient.pause() will call pause() method of the script
"""

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class PauseService(ServiceBase):
    """Makes PauseFlag instance visible on pylabnet network.

    Once the script is instantiated, assign it as the module to
    PauseService instance:
        pause_service_instance.assign_module(script_instance)
    """

    def exposed_pause(self):

        if isinstance(self._module, list):
            for module in self._module:
                module.pause()
            return 0

        else:
            return self._module.pause()


class PauseClient(ClientBase):
    """Client to send stop request to the script.

    Call of client_instance.pause() will call pause() method of the script
    """

    def pause(self):
        return self._service.exposed_pause()
