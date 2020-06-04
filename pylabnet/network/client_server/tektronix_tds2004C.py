
import pickle
import numpy as np
import matplotlib.pyplot as plt

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase
from pylabnet.gui.igui.iplot import SingleTraceFig, MultiTraceFig


class Service(ServiceBase):

    def exposed_reset(self):
        return self._module.reset()

    def exposed_get_trigger_source(self):
        return self._module.get_trigger_source()

    def exposed_set_trigger_source(self, trigger_source):
        return self._module.set_trigger_source(trigger_source)

    def exposed_set_timing_scale(self, scale):
        return self._module.set_timing_scale(scale)

    def exposed_get_timing_scale(self):
        return self._module.get_timing_scale()

    def exposed_set_single_run_acq(self):
        return self._module.set_single_run_acq()

    def exposed_acquire_single_run(self):
        return self._module.acquire_single_run()

    def exposed_read_out_trace(self, channel, curve_res):
        trace = self._module.read_out_trace(channel, curve_res)
        return pickle.dumps(trace)

    def exposed_show_trace(self, channel):
        return self._module.show_trace(channel)

    def exposed_hide_trace(self, channel):
        return self._module.hide_trace(channel)

    def exposed_get_channel_attenuation(self, channel):
        return self._module.get_channel_attenuation(channel)

    def exposed_set_channel_attenuation(self, channel, attenuation):
        return self._module.set_channel_attenuation(channel, attenuation)

    def exposed_get_channel_scale(self, channel):
        return self._module.get_channel_scale(channel)

    def exposed_set_channel_scale(self, channel, range):
        return self._module.set_channel_scale(channel, range)

    def exposed_get_channel_pos(self, channel):
        return self._module.get_channel_pos(channel)

    def exposed_set_channel_pos(self, channel, pos):
        return self._module.set_channel_pos(channel, pos)

    def exposed_get_horizontal_position(self):
        return self._module.get_horizontal_position()

    def exposed_set_horizontal_position(self, hor_pos):
        return self._module.set_horizontal_position(hor_pos)

    def exposed_trig_level_to_fifty(self):
        return self._module.trig_level_to_fifty()

    def exposed_get_trigger_level(self):
        return self._module.get_trigger_level()

    def exposed_set_trigger_level(self, trigger_level):
        return self._module.set_trigger_level(trigger_level)

    def exposed_query(self, command):
        query = self._module.device.query(command)
        return pickle.dumps(query)

    def exposed_write(self, command):
        return self._module.device.write(command)

    def exposed_extract_params(self, command, value):
        val = self._module.extract_params(command, value)
        return pickle.dumps(val)


class Client(ClientBase):

    def reset(self):
        return self._service.exposed_reset()

    def get_trigger_source(self):
        return self._service.exposed_get_trigger_source()

    def set_trigger_source(self, trigger_source):
        return self._service.exposed_set_trigger_source(trigger_source)

    def set_timing_scale(self, scale):
        return self._service.exposed_set_timing_scale(scale)

    def get_timing_scale(self):
        return self._service.exposed_get_timing_scale()

    def set_single_run_acq(self):
        return self._service.exposed_set_single_run_acq()

    def acquire_single_run(self):
        return self._service.exposed_acquire_single_run()

    def read_out_trace(self, channel, curve_res=1):
        pickled_trace = self._service.exposed_read_out_trace(
            channel,
            curve_res
        )
        return pickle.loads(pickled_trace)

    def show_trace(self, channel):
        return self._service.exposed_show_trace(channel)

    def hide_trace(self, channel):
        return self._service.exposed_hide_trace(channel)

    def get_channel_attenuation(self, channel):
        return self._service.exposed_get_channel_attenuation(channel)

    def set_channel_attenuation(self, channel, attenuation):
        return self._service.exposed_set_channel_attenuation(
            channel,
            attenuation
        )

    def get_channel_scale(self, channel):
        return self._service.exposed_get_channel_scale(channel)

    def set_channel_scale(self, channel, range):
        return self._service.exposed_set_channel_scale(channel, range)

    def get_channel_pos(self, channel):
        return self._service.exposed_get_channel_pos(channel)

    def set_channel_pos(self, channel, pos):
        return self._service.exposed_set_channel_pos(channel, pos)

    def get_horizontal_position(self):
        return self._service.exposed_get_horizontal_position()

    def set_horizontal_position(self, hor_pos):
        return self._service.exposed_set_horizontal_position(hor_pos)

    def trig_level_to_fifty(self):
        return self._service.exposed_trig_level_to_fifty()

    def get_trigger_level(self):
        return self._service.exposed_get_trigger_level()

    def set_trigger_level(self, trigger_level):
        return self._service.exposed_set_trigger_level(trigger_level)

    def query(self, command):
        query = self._service.exposed_query(command)
        return pickle.loads(query)

    def write(self, command):
        return self._service.exposed_write(command)

    def extract_params(self, command, value):
        val = self._service.exposed_extract_params(command, value)
        return pickle.loads(val)

    def plot_traces(self, channel_list, curve_res=1, staggered=True, reps=1):
        """Plot traces.

        :channel_list: (list or string) List of channel names.
        :curve_res: (int) Bit resolution of signal value (1 or 2).
        :staggered: (boolean) If true, plot every trace in a subplot, if false,
            plot all traces in one plot.
        :reps: How many traces to acquire and plot.
        """

        # If only one channel provided, make a list out of it.
        if type(channel_list) is not list:
            channel_list = [channel_list]

        num_channels = len(channel_list)

        # Read out number of points per trace.
        num_points = self.query('WFMPre:NR_Pt?')
        num_points = int(self.extract_params(':WFMPRE:NR_PT', num_points))

        results_array = np.zeros((num_channels, reps, 2, num_points))

        # Retrieve results.
        for i, channel in enumerate(channel_list):
            for j in range(reps):
                trace_dict = self.read_out_trace(
                        channel,
                        curve_res
                    )
                results_array[i, j, 0, :] = trace_dict['ts']
                results_array[i, j, 1, :] = trace_dict['trace']

        if not num_channels == 1 and staggered:

            # if staggered:
            #     fig, axs = plt.subplots(
            #         num_channels,
            #         figsize=(8, 6),
            #         sharex=True,
            #         )

            #     for i, channel in enumerate(channel_list):
            #         for j in range(reps):

            #             axs[i].plot(
            #                 trace_dict['ts']*1e6,
            #                 results_array[i, j],
            #                 label=channel
            #             )
            #             fig.tight_layout()

            #             axs[i].legend()

            #     y_unit = trace_dict['y_unit']

            #     fig.text(
            #         0.5,
            #         -0.04,
            #         r'Time since trigger [$\mu$s]',
            #         ha='center'
            #     )

            #     fig.text(
            #         -0.04,
            #         0.5,
            #         f"Signal [{y_unit}]",
            #         va='center',
            #         rotation='vertical'
            #     )
            pass

        else:

            # Index counter for iplot.
            ctr = 0

            # List containing channel names.
            ch_names = []
            for i, channel in enumerate(channel_list):
                for j in range(reps):
                    ch_names.append(channel)

            # Now build up the plot.
            multi_trace = MultiTraceFig(ch_names=ch_names)
            for i, channel in enumerate(channel_list):
                for j in range(reps):
                    multi_trace.set_data(
                        results_array[i, j, 0, :],
                        results_array[i, j, 1, :],
                        ctr
                    )
                    multi_trace.set_lbls(
                        x_str='Time since trigger [s]',
                        y_str='Signal [V]'
                    )
                    ctr += 1

            multi_trace.show()
