import numpy as np


class Measurement:
    def __init__(self, p_gen, mw_src, ctr, freq_ar, mw_pwr, gui_obj=None):

        # Hardware objects
        self._p_gen = p_gen
        self._mw_src = mw_src
        self._ctr = ctr

        self._p_gen.activate_interface()
        self._mw_src.activate_interface()
        self._ctr.activate_interface()

        self._pwr = mw_pwr
        self._pb = None

        # Sweep array
        self._swp_ar = freq_ar
        self._swp_idx = 0

        # Data arrays
        self.ar_1d = np.zeros(len(self._swp_ar))
        self.ar_2d = np.zeros(shape=(len(self._swp_ar), 1))

        # GUI
        if gui_obj is not None:
            self._fig_1d = gui_obj.fig_1d
            self._fig_2d = gui_obj.fig_2d
            self._pog_bar = gui_obj.prog_bar

    def setup_hardware(self):
        self._mw_src.set_pwr(pwr=self._pwr)
        self._gen_pb()
        self._p_gen.write(self._pb)
        pass

    def make_iter(self):
        # Do some operation on hardware

        # Update plot_1d, plot_2d, pog_bar
        pass

    def stop(self):
        self._mw_src.off()

    def clear(self):
        pass

    def _gen_pb(self):
        self._pb = None
        pass


