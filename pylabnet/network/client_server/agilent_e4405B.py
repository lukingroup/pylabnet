
import pickle
import numpy as np
import matplotlib.pyplot as plt

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_display_off(self):
        return self._module.display_off()

    def exposed_display_on(self):
        return self._module.display_on()

    def exposed_set_attenuation(self, db):
        return self._module.set_attenuation(db)

    def exposed_set_reference_level(self, db):
        return self._module.set_reference_level(db)

    def exposed_set_center_frequency(self, center_frequency):
        return self._module.set_center_frequency(center_frequency)

    def exposed_set_frequency_span(self, frequency_span):
        return self._module.set_frequency_span(frequency_span)

    def exposed_read_trace(self):
        trace = self._module.read_trace()
        return pickle.dumps(trace)

    def exposed_query(self, command):
        query = self._module.device.query(command)
        return pickle.dumps(query)

    def exposed_write(self, command):
        return self._module.device.write(command)

    def exposed_acquire_background_spectrum(self, num_point):
        return self._module.acquire_background_spectrum(num_point)

    def exposed_get_background(self):
        background = self._module.get_background()
        return pickle.dumps(background)


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def display_off(self):
        return self._service.exposed_display_off()

    def display_on(self):
        return self._service.exposed_display_on()

    def set_attenuation(self, db):
        return self._service.exposed_set_attenuation(db)

    def set_reference_level(self, db):
        return self._service.exposed_set_reference_level(db)

    def set_center_frequency(self, center_frequency):
        return self._service.exposed_set_center_frequency(center_frequency)

    def set_frequency_span(self, frequency_span):
        return self._service.exposed_set_frequency_span(frequency_span)

    def read_trace(self):
        pickled_trace = self._service.exposed_read_trace()
        return pickle.loads(pickled_trace)

    def write(self, command):
        return self._service.exposed_write(command)

    def query(self, command):
        pickled_query = self._service.exposed_query(command)
        return pickle.loads(pickled_query)

    def acquire_background_spectrum(self, num_point=100, nocheck=True):

        if not nocheck:
            print("Please make sure that spectrum analyzer is measuring noise floor, i.e. no input signals are switched on. Type 'y' to confirm.")
            a = input()
            if a == 'y':
                return self._service.acquire_background_spectrum(num_point)
            else:
                print('Wrong input, returns.')
                return

    def get_background(self):
        pickled_background = self._service.exposed_get_background()

        background = pickle.loads(pickled_background)

        if not type(background) == np.ndarray:
            print('No background acquired. Run acquire_background_spectrum() to acquire background.')

        return pickle.loads(pickled_background)

    def plot_trace(self, trace=None, background_substract=False):
        """Reads and plots trace

        :trace: Trace to plot. If none, acquire new trace.
        :background_substract: If True, substract background from trace
        """

        # If not trace furnished, acquired trace.
        if trace is None:
            trace = self.read_trace()

        # Substract background
        if background_substract:

            # Try to retrieve background
            background = self.get_background()

            # Check if background was successfully retrieved
            if not type(background) == np.ndarray:
                print()
                return

            trace[:, 1] = trace[:, 1] - background[:, 1]
            ylabel = 'Power ratio above noise floor [dB]'
        else:
            ylabel = 'Power [dBm]'

        # Plot trace
        plt.figure()
        plt.plot(trace[:, 0] / 1e9, trace[:, 1])
        plt.xlabel('Frequency [GHz]')
        plt.ylabel(ylabel)
        plt.show()

    def plot_background(self):
        """Reads and plots background trace"""

        # Try to retrieve background.
        background = self.get_background()

        # Check if background was successfully retrieved.
        if not type(background) == np.ndarray:
            print('No background acquired. Run acquire_background_spectrum() to acquire background.')
            return

        self.plot_trace(background, background_substract=False)
