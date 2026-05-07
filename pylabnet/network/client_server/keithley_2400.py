from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_clear_status(self):
        return self._module.clear_status()

    def exposed_close(self):
        return self._module.close()

    def exposed_identify(self):
        return self._module.identify()

    def exposed_get_error(self):
        return self._module.get_error()

    def exposed_output_on(self):
        return self._module.output_on()

    def exposed_output_off(self):
        return self._module.output_off()

    def exposed_is_output_on(self):
        return self._module.is_output_on()

    def exposed_wait_complete(self):
        return self._module.wait_complete()

    def exposed_set_voltage_source(self):
        return self._module.set_voltage_source()

    def exposed_set_current_source(self):
        return self._module.set_current_source()

    def exposed_get_source_function(self):
        return self._module.get_source_function()

    def exposed_set_voltage(self, voltage):
        return self._module.set_voltage(voltage)

    def exposed_get_voltage(self):
        return self._module.get_voltage()

    def exposed_set_current(self, current):
        return self._module.set_current(current)

    def exposed_get_current(self):
        return self._module.get_current()

    def exposed_set_current_compliance(self, current):
        return self._module.set_current_compliance(current)

    def exposed_get_current_compliance(self):
        return self._module.get_current_compliance()

    def exposed_set_voltage_compliance(self, voltage):
        return self._module.set_voltage_compliance(voltage)

    def exposed_get_voltage_compliance(self):
        return self._module.get_voltage_compliance()

    def exposed_is_in_current_compliance(self):
        return self._module.is_in_current_compliance()

    def exposed_is_in_voltage_compliance(self):
        return self._module.is_in_voltage_compliance()

    def exposed_is_in_compliance(self):
        return self._module.is_in_compliance()

    def exposed_set_4wire_sense(self, state):
        return self._module.set_4wire_sense(state)

    def exposed_get_4wire_sense(self):
        return self._module.get_4wire_sense()

    def exposed_set_measure_current(self):
        return self._module.set_measure_current()

    def exposed_set_measure_voltage(self):
        return self._module.set_measure_voltage()

    def exposed_read_current(self):
        return self._module.read_current()

    def exposed_read_voltage(self):
        return self._module.read_voltage()

    def exposed_read_voltage_current(self):
        return self._module.read_voltage_current()


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def clear_status(self):
        return self._service.exposed_clear_status()

    def close(self):
        return self._service.exposed_close()

    def identify(self):
        return self._service.exposed_identify()

    def get_error(self):
        return self._service.exposed_get_error()

    def output_on(self):
        return self._service.exposed_output_on()

    def output_off(self):
        return self._service.exposed_output_off()

    def is_output_on(self):
        return self._service.exposed_is_output_on()

    def wait_complete(self):
        return self._service.exposed_wait_complete()

    def set_voltage_source(self):
        return self._service.exposed_set_voltage_source()

    def set_current_source(self):
        return self._service.exposed_set_current_source()

    def get_source_function(self):
        return self._service.exposed_get_source_function()

    def set_voltage(self, voltage):
        return self._service.exposed_set_voltage(voltage)

    def get_voltage(self):
        return self._service.exposed_get_voltage()

    def set_current(self, current):
        return self._service.exposed_set_current(current)

    def get_current(self):
        return self._service.exposed_get_current()

    def set_current_compliance(self, current):
        return self._service.exposed_set_current_compliance(current)

    def get_current_compliance(self):
        return self._service.exposed_get_current_compliance()

    def set_voltage_compliance(self, voltage):
        return self._service.exposed_set_voltage_compliance(voltage)

    def get_voltage_compliance(self):
        return self._service.exposed_get_voltage_compliance()

    def is_in_current_compliance(self):
        return self._service.exposed_is_in_current_compliance()

    def is_in_voltage_compliance(self):
        return self._service.exposed_is_in_voltage_compliance()

    def is_in_compliance(self):
        return self._service.exposed_is_in_compliance()

    def set_4wire_sense(self, state):
        return self._service.exposed_set_4wire_sense(state)

    def get_4wire_sense(self):
        return self._service.exposed_get_4wire_sense()

    def set_measure_current(self):
        return self._service.exposed_set_measure_current()

    def set_measure_voltage(self):
        return self._service.exposed_set_measure_voltage()

    def read_current(self):
        return self._service.exposed_read_current()

    def read_voltage(self):
        return self._service.exposed_read_voltage()

    def read_voltage_current(self):
        return self._service.exposed_read_voltage_current()
