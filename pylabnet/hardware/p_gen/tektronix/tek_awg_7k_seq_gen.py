import copy


class TekAWG7kSeqGen:

    def __init__(self, tek_awg_7k_inst):
        self._dev = tek_awg_7k_inst

        # Channel name map: user-friendly to device-native
        self.map_dict = None

        self.reset()

    def reset(self):
        """ Interface-level reset

        Resets everything, except for hardware settings to which
        the above-lying logic has no access.

        :return: 0 - Success code
        """

        # Save all the settings, which were not given by above-lying logic
        tmp_interleave = self._dev.get_interleave()
        tmp_samp_rate = self._dev.get_samp_rate()
        tmp_anlg_level = self._dev.get_analog_level()
        tmp_digital_level = self._dev.get_digital_level()

        # Full hardware reset
        self._dev.reset()

        # Restore these settings
        self._dev.set_mode(mode_string='S')
        self._dev.set_interleave(state=tmp_interleave)
        self._dev.set_samp_rate(samp_rate=tmp_samp_rate)
        self._dev.set_analog_level(level_dict=tmp_anlg_level)
        self._dev.set_digital_level(level_dict=tmp_digital_level)

        return 0

    def start(self):
        return self._dev.start()

    def stop(self):
        return self._dev.stop()

    def write_wfm(self, pb_obj, collapse=False, strict_hrdw_seq=False, len_adj=True):

        # Map user-friendly names onto physical channel numbers
        pb_obj = copy.deepcopy(pb_obj)
        pb_obj.ch_map(map_dict=self.map_dict)

        # Fill unused channels with default values
        pb_obj = self._dev.fill_unused_chs(pb_obj=pb_obj)

        if collapse:
            self._dev.write_wfm_zip(
                pb_obj=pb_obj,
                len_adj=len_adj
            )
        else:
            self._dev.write_wfm(
                pb_obj=pb_obj,
                len_adj=len_adj,
                strict_hrdw_seq=strict_hrdw_seq
            )

    def del_wfm(self, wfm_name):
        pass

    def write_seq(self, seq_table):
        pass

