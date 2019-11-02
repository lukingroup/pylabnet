from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.hardware.interface.simple_p_gen import SimplePGenInterface
from pylabnet.gui.output_interface import TraceInterface, HeatMapInterface, PBarInterface
import pulseblock.pulse as po
import pulseblock.pulse_block as pb
import numpy as np
import time


class CountTrace:
    def __init__(self):

        # Hardware instances
        self._gated_ctr = None
        self._p_gen = None
        self._rfcs = None

        # GUI instances
        self._1d_trace = None
        self._2d_heat_map = None
        self._p_bar = None

        # Parameters
        self._laser_dur = None
        self._l_margin = None
        self._r_margin = None
        self._n_pts = None
        self._relax = None
        self._hrdw_reps = None
        self._soft_reps = None

        # Internal data arrays
        self.t_ar = None  # 1D numpy float array
        self.sum_ar = None  # 1D numpy float array
        self.raw_ar = None  # 2D numpy float array

        # Current sweep index
        self._is_running = False
        self._soft_rep_idx = 0

        # Approximate duration of full pulse block
        # [for gated_ctr.get_count_ar() timeout]
        self._pb_dur = -1

    # User interface methods

    def set_hardware(self, gated_ctr, p_gen, rfcs=None):

        # Sanity checks
        if not isinstance(gated_ctr, GatedCtrInterface):
            raise TypeError(
                'set_hardware(): given gated_ctr instance does not inherit from GatedCtrInterface'
            )
        if not isinstance(p_gen, SimplePGenInterface):
            raise TypeError(
                'set_hardware(): given p_gen instance does not inherit from SimplePGenInterface'
            )

        # Save references in internal variables
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
                x_str='Time [s]',
                y_str='Counts'
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_lbls(
                x_str='Time [s]',
                y_str='Repetition'
            )

        return 0

    def set_params(self, laser_dur, l_margin, r_margin, n_pts, relax, hrdw_reps, soft_reps):
        # Save params to internal variables
        self._laser_dur = laser_dur
        self._l_margin = l_margin
        self._r_margin = r_margin
        self._n_pts = n_pts
        self._relax = relax
        self._hrdw_reps = hrdw_reps
        self._soft_reps = soft_reps

        # Allocate data arrays
        self._alloc_ars()

        return 0

    def run(self, clear_data=False, rfcs=True, rfcs_dur=12, rfcs_every=1):

        try:

            self._setup_hardware()

            # Remove data from previous runs
            if clear_data:
                self.clear_data()

            self._is_running = True

            # Main measurement iteration loop
            while self._is_running and self._soft_rep_idx < self._soft_reps:

                # Run actual iteration
                self._make_iter()

                # Increment _soft_rep_idx only after the iteration is complete
                # (if iteration is interrupted before completion it should
                # not count as done)
                self._soft_rep_idx += 1

                # Update GUI
                self._update_gui()

                if rfcs and self._soft_rep_idx % rfcs_every == 0:
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
            rep_num=self._hrdw_reps
        )

        return 0

    # Technical methods

    @staticmethod
    def _gen_rfcs_block():

        optimize_pb = pb.PulseBlock(
            p_obj_list=[
                po.PTrue(ch='aom', dur=1e-6)
            ],
            dflt_dict=dict(aom=po.DTrue())
        )

        return optimize_pb

    def _alloc_ars(self):
        """Allocate/re-allocate data arrays

        :return: (int) status code: 0 - Ok
                            Exception - Error
        """

        # Delete existing arrays
        if self.t_ar is not None:
            del self.t_ar

        if self.sum_ar is not None:
            del self.sum_ar

        if self.raw_ar is not None:
            del self.raw_ar

        # Allocate empty arrays
        self.t_ar = np.linspace(
            start=-self._l_margin,
            stop=self._laser_dur+self._r_margin,
            num=self._n_pts
        )
        self.sum_ar = np.zeros(
            shape=self._n_pts,
            dtype=float
        )
        self.raw_ar = np.zeros(
            shape=(self._soft_reps, self._n_pts),
            dtype=float
        )

        return 0

    def _setup_hardware(self):

        # Activate interface: "logic-reset" - not full hardware reset,
        # but reset of all the params to which any logic has access
        # (including params used by any other interface to this device)
        # and configuring the device to operate for this interface
        self._gated_ctr.activate_interface()
        self._p_gen.activate_interface()

        # Init gated_ctr
        self._gated_ctr.init_ctr(
            bin_number=self._n_pts * self._hrdw_reps,
            gate_type='RR'
        )

        # Configure p_gen
        self._p_gen.write(
            pb_obj=self._gen_p_block()
        )
        self._p_gen.set_rep(
            rep_num=self._hrdw_reps
        )

        return 0

    def _gen_p_block(self):

        count_trace_pb = pb.PulseBlock()

        # Sample clock
        t_step = (self._l_margin + self._laser_dur + self._r_margin) / self._n_pts

        for idx in range(self._n_pts):
            count_trace_pb.append(
                p_obj=po.PTrue(
                    ch='ctr_gate',
                    dur=t_step / 2,
                    t0=t_step / 2
                )
            )

        # Laser pulse
        count_trace_pb.insert(
            p_obj=po.PTrue(
                ch='aom',
                dur=self._laser_dur,
                t0=self._l_margin
            )
        )

        # Relaxation period and all off pulse block
        count_trace_pb.append(
            p_obj=po.PFalse(
                ch='aom',
                dur=t_step,
                t0=self._relax
            )
        )
        count_trace_pb.append(
            p_obj=po.PFalse(
                ch='ctr_gate',
                dur=t_step,
            )
        )

        # Duration of full PB
        # [for gated_ctr.get_count_ar() timeout]
        self._pb_dur = count_trace_pb.dur

        # Default value
        count_trace_pb.dflt_dict = dict(
            aom=po.DFalse(),
            ctr_gate=po.DFalse()
        )

        return count_trace_pb

    def _make_iter(self):

        self._gated_ctr.start_counting()
        self._p_gen.start()

        # Read data from counter
        timeout = max(
            10 * self._pb_dur * self._hrdw_reps,
            1
        )
        flat_cnt_ar = self._gated_ctr.get_count_ar(timeout=timeout)

        # Sum counts from different hardware repetitions
        cnt_ar = np.reshape(
            a=flat_cnt_ar,
            newshape=(self._hrdw_reps, self._n_pts)
        )
        cnt_ar = np.sum(a=cnt_ar, axis=0)

        # Update data arrays
        self.raw_ar[self._soft_rep_idx][:] = cnt_ar
        self.sum_ar[:] = np.sum(
            a=self.raw_ar,
            axis=0
        )

        self._p_gen.stop()

    def _update_gui(self):

        if self._1d_trace is not None:
            self._1d_trace.set_data(
                x_ar=self.t_ar[:-1],
                y_ar=self.sum_ar
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_data(
                x_ar=self.t_ar[:-1],
                y_ar=np.arange(start=1, stop=self._soft_rep_idx + 1),
                z_ar=self.raw_ar[:self._soft_rep_idx, :-1]
            )

        if self._p_bar is not None:
            self._p_bar.set_value(
                value=100 * self._soft_rep_idx / self._soft_reps
            )

    def _hardware_off(self):
        self._p_gen.stop()
        self._gated_ctr.terminate_counting()
