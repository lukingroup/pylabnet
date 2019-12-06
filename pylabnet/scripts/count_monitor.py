from pylabnet.hardware.interface.ctr_monitor import CtrMonitorInterface
from pylabnet.gui.output_interface import TraceInterface, MultiTraceInterface
import numpy as np

class CountMonitor:
    def __init__(self):
        self._ctr = None
        self._nd_trace = None
        self._is_running = False
        self._bin_width = None
        self._n_bins = None
        
    def set_hardware(self, ctr):

        # Initialize counter instance
        self._ctr = ctr

    def set_gui(self, trace):

        self._nd_trace = trace
        
        # Set axes labels
        if self._nd_trace is not None:
            self._nd_trace.set_lbls(
                x_str='Time (s)',
                y_str='Counts (Hz)'
            )

    def set_params(self, bin_width=1e9, n_bins=1e4, ch_list=[1]):

            # Save params to internal variables
            self._bin_width = int(bin_width)
            self._n_bins = int(n_bins)

            # Configure counting channels
            self._ctr.set_channels(ch_list=ch_list)
    
    def run(self):

        try:

            # Start the counter with desired parameters
            self._is_running = True
            self._ctr.start_counting(bin_width=self._bin_width, n_bins=self._n_bins)

            # Show plot
            self._nd_trace.show()

            # Continuously update data until paused
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    def pause(self):

        self._is_running = False

    def resume(self):

        try:
            self._is_running = True

            # Clear counter and resume plotting
            self._ctr.clear_counter()
            while self._is_running:
                self._update_output()

        except Exception as exc_obj:
            self._is_running = False
            raise exc_obj

    # Technical methods

    def _update_output(self):

        # Update all active channels
        x_axis = self._ctr.get_x_axis()/1e12
        counts = self._ctr.get_counts()
        counts_per_sec = counts*(1e12/self._bin_width)
        noise = np.sqrt(counts)*(1e12/self._bin_width)
        for index, count_trace in enumerate(counts_per_sec):
            self._nd_trace.set_data(
                x_ar=x_axis,
                y_ar=count_trace,
                ind=index,
                noise=noise[index]
            )
