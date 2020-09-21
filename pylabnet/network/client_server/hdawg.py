from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_set_direct_user_register(self, awg_num, index, value):
        return self._module.set_direct_user_register(awg_num, index, value)

    def exposed_get_direct_user_register(self, awg_num, index):

        return self._module.get_direct_user_register(awg_num, index)



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
