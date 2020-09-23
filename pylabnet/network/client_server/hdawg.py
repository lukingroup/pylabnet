from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_direct_user_register(self, awg_num, index, value):
        return self._module.set_direct_user_register(awg_num, index, value)

    def exposed_get_direct_user_register(self, awg_num, index):

        return self._module.get_direct_user_register(awg_num, index)

    def exposed_geti(self, node):
        return self._module.geti(node)

    def exposed_seti(self, node, new_int):
        return self._module.seti(node, new_int)



class Client(ClientBase):

    def set_direct_user_register(self, awg_num, index, value):
        """ Sets a user register to a desired value

        :param awg_num: (int) index of awg module
        :param index: (int) index of user register (from 0-15)
        :param value: (int) value to set user register to
        """
        return self._service.exposed_set_direct_user_register(awg_num, index, value)

    def get_direct_user_register(self, awg_num, index):
        """ Gets a user register to a desired value

        :param awg_num: (int) index of awg module
        :param index: (int) index of user register (from 0-15)
        """

        return self._service.exposed_get_direct_user_register(awg_num, index)

    def geti(self, node):
        """
        Wrapper for daq.getInt commands. For instance, instead of
        daq.getInt('/dev8040/sigouts/0/busy'), write

        hdawg.geti('sigouts/0/busy')

        :node: Node which will be appended to '/device_id/'
        """
        return self._service.exposed_geti(node)

    def seti(self, node, new_int):
        """
        Warapper for daq.setInt commands. For instance, instead of
        daq.setInt('/dev8040/sigouts/0/on', 1), write

        hdawg.seti('sigouts/0/on, 1)

        :node: Node which will be appended to '/device_id/'
        :new_int: New value for integer
        """
        return self._service.exposed_seti(node, new_int)
