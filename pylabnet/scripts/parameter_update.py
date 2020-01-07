"""
Set of tools to update parameters of a currently running script

Steps:
- the script class should have public method update_parameters(params),
  which will be called by client through RPyC link
- once the script is instantiated, assign it as the module to
  UpdateService instance:
      update_service_instance.assign_module(script_instance)
- instantiate UpdateClient in a different process
- call of UpdateClient.update_parameters(params) will call update_parameters(param) method of the script
"""

from pylabnet.core.service_base import ServiceBase
from pylabnet.core.client_base import ClientBase


class UpdateService(ServiceBase):
    """
    Makes parameter updating service accessible through pylabnet.

    Once Service is instantiated, assign a script module to it by calling:
        update_service_instance.assign_module(script_instance)
    """

    def exposed_update_parameters(self, params):

        return self._module.update_parameters(params)


class UpdateClient(ClientBase):
    """
    Creates a client that can update parameters over pylabnet.

    To update parameters, call:
        update_client_instance.update_parameters(params)
    This will call the following line of the module:
        module.update_parameters(params)
    """

    def update_parameters(self, params):

        return self._service.exposed_update_parameters(params)