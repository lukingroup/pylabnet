from pylabnet.hardware.interface.mw_src import MWSrcInterface
from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.hardware.interface.simple_p_gen import SimplePGenInterface
from pylabnet.gui.output_interface import TraceInterface, HeatMapInterface, PBarInterface
import pylabnet.utils.pulseblock.pulse as po
import pylabnet.utils.pulseblock.pulse_block as pb
import numpy as np
import time

# TODO: add readout window and refocus as parameters


class Rabi:
    def __init__(self):

        # Hardware instances
        self._mw_src = None
        self._gated_ctr = None
        self._p_gen = None
        self._rfcs = None

        # GUI instances
        self._1d_trace = None
        self._2d_heat_map = None
        self._p_bar = None

        # Parameters
        #  - Rabi measurement
        self._freq = None
        self._pwr = None

        self._tau_start = None
        self._tau_stop = None
        self._n_pts = None

        #  - repetitions
        self._n_hrdw_reps = None
        self._n_soft_reps = None

        #  - PulseBlock params
        self._aom_delay = None

        # Internal data arrays
        self.tau_ar = None  # 1D numpy float array
        self.avg_ar = None  # 1D numpy float array
        self.raw_ar = None  # 2D numpy float array

        # Current software-rep index
        self._is_running = False
        self._soft_rep_idx = 0

        # Approximate duration of full RabiPB
        # [for gated_ctr.get_count_ar() timeout]
        self._rabi_pb_dur = -1

    # User interface methods

    def set_hardware(self, mw_src, gated_ctr, p_gen, rfcs=None):

        # Sanity checks
        if not isinstance(mw_src, MWSrcInterface):
            raise TypeError(
                'set_hardware(): given mw_src instance does not inherit from MWSrcInterface'
            )
        if not isinstance(gated_ctr, GatedCtrInterface):
            raise TypeError(
                'set_hardware(): given gated_ctr instance does not inherit from GatedCtrInterface'
            )
        if not isinstance(p_gen, SimplePGenInterface):
            raise TypeError(
                'set_hardware(): given p_gen instance does not inherit from SimplePGenInterface'
            )

        # Save references in internal variables
        self._mw_src = mw_src
        self._gated_ctr = gated_ctr
        self._p_gen = p_gen

        if rfcs is not None:
            self._rfcs = rfcs

        return 0

    def set_gui(self, trace=None, heat_map=None, p_bar=None):

        # Sanity checks
        if trace is not None and not isinstance(trace, TraceInterface):
            raise TypeError(
                'set_gui(): given trace instance does not inherit from TraceInterface'
            )
        if heat_map is not None and not isinstance(heat_map, HeatMapInterface):
            raise TypeError(
                'set_gui(): given heat_map instance does not inherit from HeatMapInterface'
            )
        if p_bar is not None and not isinstance(p_bar, PBarInterface):
            raise TypeError(
                'set_gui(): given p_bar instance does not inherit from PBarInterface'
            )

        # Save references in internal variables
        # [None if not given]
        self._1d_trace = trace
        self._2d_heat_map = heat_map
        self._p_bar = p_bar

        # Set axes labels
        if self._1d_trace is not None:
            self._1d_trace.set_lbls(
                x_str='tau [s]',
                y_str='State'
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_lbls(
                x_str='tau [s]',
                y_str='Repetition'
            )

        return 0

    def set_params(self, freq, pwr,
                   tau_start, tau_stop, n_pts,
                   n_soft_reps, n_hrdw_reps,
                   aom_delay=500e-9):

        self._freq = freq
        self._pwr = pwr
        self._tau_start = tau_start
        self._tau_stop = tau_stop
        self._n_pts = n_pts
        self._n_soft_reps = n_soft_reps
        self._n_hrdw_reps = n_hrdw_reps
        self._aom_delay = aom_delay

        # Allocate data arrays
        self._alloc_ars()

        return 0

    def run(self, clear_data=False, rfcs=True, rfcs_dur=12):

        try:

            self._setup_hardware()

            # Remove data from previous runs
            if clear_data:
                self.clear_data()

            self._is_running = True

            # Main measurement iteration loop
            while self._is_running and self._soft_rep_idx < self._n_soft_reps:

                # Run actual iteration
                self._make_iter()

                # Increment _soft_rep_idx only after the iteration is complete
                # (if iteration is interrupted before completion it should
                # not count as done)
                self._soft_rep_idx += 1

                # Update GUI
                self._update_gui()

                if rfcs:
                    self.rfcs(rfcs_dur=rfcs_dur)

            # Measurement is complete or paused
            self._hardware_off()
            self._is_running = False
            # [The main difference from interruption due to exception is that
            # here the loop waits for the iteration in progress to complete
            # before switching hardware off]

            return 0

        # Any other error
        except Exception as exc_obj:
            self.interrupt()
            raise exc_obj

    def pause(self):

        # The main difference between pause and interruption due to exception
        # is that, after calling pause(), the loop waits for the iteration in
        # progress to complete.

        self._is_running = False
        return 0

    def interrupt(self):
        self._hardware_off()
        self._is_running = False
        return 0

    def clear_data(self):

        # Reset sweep index
        self._soft_rep_idx = 0

        # Re-allocate data arrays
        self._alloc_ars()

        return 0

    # Technical methods

    def _alloc_ars(self):
        """Allocate/re-allocate data arrays

        :return: (int) status code: 0 - Ok
                            Exception - Error
        """

        # Delete existing arrays
        if self.tau_ar is not None:
            del self.tau_ar

        if self.avg_ar is not None:
            del self.avg_ar

        if self.raw_ar is not None:
            del self.raw_ar

        # Allocate empty arrays
        self.tau_ar = np.linspace(
            start=self._tau_start,
            stop=self._tau_stop,
            num=self._n_pts
        )
        self.avg_ar = np.zeros(
            shape=self._n_pts,
            dtype=float
        )
        self.raw_ar = np.zeros(
            shape=(self._n_soft_reps, self._n_pts),
            dtype=float
        )

        return 0

    def _setup_hardware(self):

        # Activate interface: "logic-reset" - not full hardware reset,
        # but reset of all the params to which any logic has access
        # (including params used by any other interface to this device)
        # and configuring the device to operate for this interface
        self._mw_src.activate_interface()
        self._gated_ctr.activate_interface()
        self._p_gen.activate_interface()

        # Configure mw_src
        self._mw_src.set_pwr(pwr=self._pwr)
        self._mw_src.set_freq(freq=self._freq)
        self._mw_src.on()

        # Init gated_ctr
        self._gated_ctr.init_ctr(
            bin_number=2 * self._n_pts * self._n_hrdw_reps,
            gate_type='RF'
        )

        # Configure p_gen
        self._p_gen.write(
            pb_obj=self._gen_p_block()
        )
        self._p_gen.set_rep(
            rep_num=self._n_hrdw_reps
        )

        return 0

    def _gen_p_block(self, safety_window=200e-9):

        # ========== Prepare individual blocks =========

        # ------- pre_init_pb --------
        # Long optical pumping before first pulse

        pre_init_pb = pb.PulseBlock(
            p_obj_list=[
                po.PTrue(ch='aom', dur=3e-6)
            ]
        )

        # ------- all_off_pb --------
        # Switch all channels off after the full pulse sequence

        all_off_pb = pb.PulseBlock(
            p_obj_list=[
                po.PFalse(ch='aom', dur=1e-6),
                po.PFalse(ch='mw_gate', dur=1e-6),
                po.PFalse(ch='ctr_gate', dur=1e-6)
            ]
        )

        # ========== Construct full rabi_pb =========

        rabi_pb = pb.PulseBlock(name='RabiPB')

        # Pre-init block
        rabi_pb.insert_pb(pb_obj=pre_init_pb)

        # rabi_element ** n_pts
        for tau in self.tau_ar:
            rabi_pb.append_pb(
                pb_obj=self._gen_rabi_elem(
                    tau=tau,
                    safety_window=safety_window
                )
            )

        # All-off block
        rabi_pb.append_pb(pb_obj=all_off_pb)

        # Default values
        rabi_pb.dflt_dict = dict(
            aom=po.DFalse(),
            ctr_gate=po.DFalse(),
            mw_gate=po.DFalse()
        )

        # Correct for aom delay
        rabi_pb.add_offset(
            offset_dict=dict(
                aom=-self._aom_delay
            )
        )

        # Duration of full RabiPB
        # [for gated_ctr.get_count_ar() timeout]
        self._rabi_pb_dur = rabi_pb.dur

        return rabi_pb

    @staticmethod
    def _gen_rabi_elem(tau=0, safety_window=200e-9):
        rabi_elem = pb.PulseBlock()

        # Init green_aom pulse
        rabi_elem.insert(
            p_obj=po.PTrue(
                ch='aom',
                dur=2e-6 + 2*safety_window
            )
        )

        # Normalization pulse
        rabi_elem.insert(
            p_obj=po.PTrue(
                ch='ctr_gate',
                t0=1.5e-6,
                dur=0.5e-6
            )
        )

        # mw pulse
        rabi_elem.append(
            p_obj=po.PTrue(
                ch='mw_gate',
                dur=tau,
                t0=4 * safety_window
            )
        )

        tmp_dur = rabi_elem.dur + 4*safety_window

        # Readout AOM pulse
        rabi_elem.insert(
            p_obj=po.PTrue(
                ch='aom',
                dur=1e-6,
                t0=tmp_dur
            )
        )

        # readout ctr_gate pulse
        rabi_elem.insert(
            p_obj=po.PTrue(
                ch='ctr_gate',
                dur=0.5e-6,
                t0=tmp_dur
            )
        )

        return rabi_elem

    def _make_iter(self):

        self._gated_ctr.start_counting()
        self._p_gen.start()

        # Read data from counter
        timeout = 10 * self._rabi_pb_dur * self._n_hrdw_reps
        flat_cnt_ar = self._gated_ctr.get_count_ar(timeout=timeout)

        # Sum counts from different hardware repetitions
        cnt_ar = np.reshape(
            a=flat_cnt_ar,
            newshape=(self._n_hrdw_reps, 2 * self._n_pts)
        )
        cnt_ar = np.sum(a=cnt_ar, axis=0)

        # Calculate state array
        state_ar = np.divide(
            cnt_ar[1::2],  # readout counts
            cnt_ar[::2]    # normalization counts
        )

        # Update data arrays
        self.raw_ar[self._soft_rep_idx][:] = state_ar
        self.avg_ar[:] = self.raw_ar[:self._soft_rep_idx + 1].mean(axis=0)

        self._p_gen.stop()

    def rfcs(self, rfcs_dur=12):
        self._p_gen.stop()
        self._p_gen.write(
            pb_obj=self._gen_rfcs_block()
        )
        self._p_gen.set_rep(rep_num=0)
        self._p_gen.start()

        self._rfcs.rfcs()
        time.sleep(rfcs_dur)

        self._p_gen.stop()
        self._p_gen.write(
            pb_obj=self._gen_p_block()
        )
        self._p_gen.set_rep(
            rep_num=self._n_hrdw_reps
        )

        return 0

    @staticmethod
    def _gen_rfcs_block():

        optimize_pb = pb.PulseBlock()
        optimize_pb.insert(
            p_obj=po.PTrue(ch='aom', dur=1e-6)
        )
        optimize_pb.insert(
            p_obj=po.PTrue(ch='mw_gate', dur=1e-6)
        )
        optimize_pb.dflt_dict = dict(
            aom=po.DTrue(),
            mw_gate=po.DTrue()
        )
        return optimize_pb

    def _update_gui(self):

        if self._1d_trace is not None:
            self._1d_trace.set_data(
                x_ar=self.tau_ar,
                y_ar=self.avg_ar
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_data(
                x_ar=self.tau_ar,
                y_ar=np.arange(start=1, stop=self._soft_rep_idx + 1),
                z_ar=self.raw_ar[:self._soft_rep_idx]
            )

        if self._p_bar is not None:
            self._p_bar.set_value(
                value=100 * self._soft_rep_idx / self._n_soft_reps
            )

    def _hardware_off(self):
        self._mw_src.off()
        self._p_gen.stop()
        self._gated_ctr.terminate_counting()
