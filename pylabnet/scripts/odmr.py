from pylabnet.hardware.interface.mw_src import MWSrcInterface
from pylabnet.hardware.interface.gated_ctr import GatedCtrInterface
from pylabnet.hardware.interface.simple_p_gen import SimplePGenInterface
from pylabnet.gui.output_interface import TraceInterface, HeatMapInterface, PBarInterface
import pulseblock.pulse as po
import pulseblock.pulse_block as pb
import numpy as np


class ODMR:
    def __init__(self):

        # Hardware instances
        self._mw_src = None
        self._gated_ctr = None
        self._p_gen = None

        # GUI instances
        self._1d_trace = None
        self._2d_heat_map = None
        self._p_bar = None

        # Parameters
        self._start_f = None
        self._stop_f = None
        self._n_pts = None
        self._n_swps = None
        self._mw_pwr = None
        self._accum_dur = 1e-3

        # Internal data arrays
        self.freq_ar = None  # 1D numpy float array
        self.avg_ar = None  # 1D numpy float array
        self.raw_ar = None  # 2D numpy float array

        # Current sweep index
        self._is_running = False
        self._swp_idx = 0

    # User interface methods

    def set_hardware(self, mw_src, gated_ctr, p_gen):

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
                x_str='Frequency [Hz]',
                y_str='Count rate [Cts/s]'
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_lbls(
                x_str='Frequency [Hz]',
                y_str='Repetition'
            )

        return 0

    def set_params(self, start_f, stop_f, n_pts, n_swps, mw_pwr, accum_dur=1e-3):
        # Save params to internal variables
        self._start_f = start_f
        self._stop_f = stop_f
        self._n_pts = n_pts
        self._n_swps = n_swps
        self._mw_pwr = mw_pwr
        self._accum_dur = accum_dur

        # Allocate data arrays
        self._alloc_ars()

        return 0

    def run(self, clear_data=False):

        try:

            self._setup_hardware()

            # Remove data from previous runs
            if clear_data:
                self.clear_data()

            self._is_running = True

            # Main measurement iteration loop
            while self._is_running and self._swp_idx < self._n_swps:

                # Run actual iteration
                self._make_iter()

                # Increment _swp_idx only after the iteration is complete
                # (if iteration is interrupted before completion it should
                # not count as done)
                self._swp_idx += 1

                # Update GUI
                self._update_gui()

            # Measurement is complete or paused
            self._hardware_off()
            self._is_running = False
            # [The main difference from interruption due to exception is that
            # here the loop waits for the iteration in progress to complete
            # before switching hardware off]

        except KeyboardInterrupt:
            # Measurement is interrupted by user
            return self.interrupt()

        except Exception as exc_obj:
            # Any other error
            self.interrupt()
            raise exc_obj

    def run_in_bkgr(self):
        # TODO: implement
        raise NotImplementedError(
            'Running in a background thread is not implemented'
        )

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
        self._swp_idx = 0

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
        if self.freq_ar is not None:
            del self.freq_ar

        if self.avg_ar is not None:
            del self.avg_ar

        if self.raw_ar is not None:
            del self.raw_ar

        # Allocate empty arrays
        self.freq_ar = np.linspace(
            start=self._start_f,
            stop=self._stop_f,
            num=self._n_pts
        )
        self.avg_ar = np.zeros(
            shape=self._n_pts,
            dtype=float
        )
        self.raw_ar = np.zeros(
            shape=(self._n_swps, self._n_pts),
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

        # Configure mw_src to freq sweep
        self._mw_src.set_pwr(pwr=self._mw_pwr)
        self._mw_src.set_freq_swp(
            start=self._start_f,
            stop=self._stop_f,
            n_pts=self._n_pts
        )
        self._mw_src.on()

        # Init gated_ctr
        self._gated_ctr.init_ctr(
            bin_number=self._n_pts,
            gate_type='RF'
        )

        # Configure p_gen
        self._p_gen.write(
            pb_obj=self._gen_p_block()
        )
        self._p_gen.set_rep(rep_num=1)

        return 0

    def _gen_p_block(self, debug=False):

        # Technical params

        # safety window between mw_src makes a step and
        # before counter starts accumulation of counts
        safety_window = 0.1 * self._accum_dur

        # Duration of sweep-step pulse
        step_pulse_dur = 0.1 * self._accum_dur  # 200e-6

        # ========== Prepare individual blocks =========

        # ------- first_pb --------
        # First point in the sweep:
        #   mw_src should reset sweep position to start_f,
        #   so there is no need to send step_trig pulse

        first_pb = pb.PulseBlock()

        # long safety window in the beginning
        first_pb.insert(
            p_obj=po.PFalse(
                ch='ctr_gate',
                dur=self._accum_dur
            )
        )

        # first ctr_gate pulse
        first_pb.append(
            p_obj=po.PTrue(
                ch='ctr_gate',
                dur=self._accum_dur
            )
        )

        # ------- step_pb --------
        # This pb is repeated for every subsequent sweep step:
        #   send ctr_trig pulse, wait for a safety window and
        #   start accumulating pulses

        step_pb = pb.PulseBlock()

        # step pulse to mw_src
        step_pb.insert(
            p_obj=po.PTrue(
                ch='mw_step',
                dur=step_pulse_dur
            )
        )

        # ctr_gate pulse
        step_pb.append(
            p_obj=po.PTrue(
                ch='ctr_gate',
                dur=self._accum_dur,
                t0=safety_window
            )
        )

        # ------- off_pb --------
        # Once sweep is complete, set all outputs to low

        off_pb = pb.PulseBlock()

        off_pb.insert(
            p_obj=po.PFalse(
                ch='aom',
                dur=safety_window
            )
        )
        off_pb.insert(
            p_obj=po.PFalse(
                ch='mw_gate',
                dur=safety_window
            )
        )
        off_pb.insert(
            p_obj=po.PFalse(
                ch='mw_step',
                dur=safety_window
            )
        )
        off_pb.insert(
            p_obj=po.PFalse(
                ch='ctr_gate',
                dur=safety_window
            )
        )

        # ========== Construct full odmr_pb =========

        odmr_pb = pb.PulseBlock(name='ODMRPulseBlock')

        # Default values
        odmr_pb.dflt_dict = dict(
            aom=po.DFalse(),
            ctr_gate=po.DFalse(),
            mw_gate=po.DFalse(),
            mw_step=po.DFalse(),
        )

        # first_bp
        odmr_pb.insert_pb(pb_obj=first_pb)

        # append step_bp ** (_n_pts-1)
        for _ in np.arange(start=1, stop=self._n_pts):
            odmr_pb.append_pb(pb_obj=step_pb)

        # aom and mw_gate are High during the whole block
        tmp_dur = odmr_pb.dur
        odmr_pb.insert(
            p_obj=po.PTrue(ch='aom', dur=tmp_dur)
        )
        odmr_pb.insert(
            p_obj=po.PTrue(ch='mw_gate', dur=tmp_dur)
        )

        # append off_pb
        odmr_pb.append_pb(pb_obj=off_pb)

        if debug:
            return dict(
                first_pb=first_pb,
                step_pb=step_pb,
                off_pb=off_pb,
                odmr_pb=odmr_pb
            )
        else:
            return odmr_pb

    def _make_iter(self):

        self._gated_ctr.start_counting()
        self._mw_src.reset_swp_pos()
        self._p_gen.start()

        # Read data from counter
        timeout = 10 * self._accum_dur * self._n_pts
        # read and convert to numpy float array
        raw_cnt_ar = np.asarray(
            a=self._gated_ctr.get_count_ar(timeout=timeout),
            dtype=float
        )
        # calculate count rate
        cnt_rate_ar = raw_cnt_ar / self._accum_dur

        # Update data arrays
        self.raw_ar[self._swp_idx][:] = cnt_rate_ar
        self.avg_ar[:] = self.raw_ar[:self._swp_idx+1].mean(axis=0)

        self._p_gen.stop()

    def _update_gui(self):

        if self._1d_trace is not None:
            self._1d_trace.set_data(
                x_ar=self.freq_ar,
                y_ar=self.avg_ar
            )

        if self._2d_heat_map is not None:
            self._2d_heat_map.set_data(
                x_ar=self.freq_ar,
                y_ar=np.arange(start=1, stop=self._swp_idx + 1),
                z_ar=self.raw_ar[:self._swp_idx]
            )

        if self._p_bar is not None:
            self._p_bar.set_value(
                value=100 * self._swp_idx / self._n_swps
            )

    def _hardware_off(self):
        self._mw_src.off()
        self._p_gen.stop()
        self._gated_ctr.terminate_counting()
