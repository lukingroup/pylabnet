# -*- coding: utf-8 -*-

"""
This file contains the hardware module for NI PXI(PCI)-654x digital waveform generator/analyzer cards.
It only implements waveform generation functionality.
"""


from core.module import Base, ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints
from core.util.interfaces import ScalarConstraint
from collections import OrderedDict
import ctypes
from hardware.ni_hsdio.c_headers import NITypes, NIConst, build_c_func_prototypes
import numpy as np
import re
import copy


class NI654X(Base, PulserInterface):
    """ A hardware module for the Tektronix AWG7000 series for generating
            waveforms and sequences thereof.

        Example config for copy-paste:

        ni_hsdio_card:
            module.Class: 'ni_hsdio.ni_654x.NI654X'
            dev_name: PXI-6542
            NI_HSDIO_dll_path: 'C:/Program Files/IVI Foundation/IVI/Bin/niHSDIO_64.dll'

    """

    _modclass = 'ni654x'
    _modtype = 'hardware'

    # config options
    _dev_name = ConfigOption(name='dev_name', missing='error')
    _dll_path = ConfigOption(name='niHSDIO_dll_path', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # "Load" niHSDIO DLL
        self.dll = ctypes.WinDLL(self._dll_path)
        self.log.debug('{}'.format(self.dll))

        # Build prototypes (in particular, specify the return type, such that Python reads it correctly)
        build_c_func_prototypes(self.dll)

        # Create blank for the session handle
        self.handle = NITypes.ViSession()

        # Convert self._dev_name to the DLL-readable format
        self.device_name = NITypes.ViRsrc(self._dev_name.encode('ascii'))

        # Status: self._status == 0 - pulser is idle
        #         self._status > 0  - pulser is running
        #         self._status < 0  - communication error
        # Copy of this attribute is returned by self.get_status() for further use in sequence_generator_logic
        # before applying any changes
        self._status = 0

        # List of waveforms currently present in the memory
        self._wfm_list = []
        # List of sequences currently present in the memory
        self._script_list = []

        self.log.debug('Init')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Initialize Dynamic Generation session
        #   ViStatus = niHSDIO_InitGenerationSession(ViRsrc resourceName, ViBoolean IDQuery, ViBoolean
        #                                            resetDevice, ViConstString optionString, ViSession * vi);

        self.log.debug('on_activate')

        op_status = self._er_chk(
            self.dll.niHSDIO_InitGenerationSession(
                self.device_name,           # ViRsrc resourceName
                NIConst.VI_TRUE,            # ViBoolean IDQuery
                NIConst.VI_FALSE,            # ViBoolean resetDevice
                NIConst.VI_NULL,            # ViConstString optionString - not used, set to VI_NULL
                ctypes.byref(self.handle)   # ViSession * session_handle
            )
        )
        # Generate info message in the case of successful connection
        if op_status == 0:
            dev_serial_numb = self._get_attribute_string(NIConst.NIHSDIO_ATTR_SERIAL_NUMBER)
            self.log.info('Connected to NI HSDIO card {0}. Serial number: {1}. Session handle: {2}'
                          ''.format(self._dev_name, dev_serial_numb, self.handle))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self.log.debug('on_deactivate')

        # Stop generation, if it is running
        self.pulser_off()

        # Reset device
        op_status1 = self.reset()

        # Close session and free any reserved resources
        op_status2 = self._er_chk(
            self.dll.niHSDIO_close(
                self.handle     # ViSession session_handle
            )
        )

        # Generate info message in the case of successfully closed connection
        if op_status1 == 0 and op_status2 == 0:
            self.log.info('NI HSDIO {0}: Successfully closed connection and reset the card'.format(self._dev_name))

    # ################################################################
    #                    PulserInterface methods
    # ################################################################

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        op_status = self._er_chk(
            self.dll.niHSDIO_Initiate(
                self.handle
            )
        )

        # Set self._status to "Running" if Initiate was successful
        if op_status == 0:
            self._status = 1

        # FIXME: if generation mode is FINITE, the pulser will finish generation, will return to idle state,
        # FIXME: but self._states will still be 1.

        return op_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        op_status = self._er_chk(
            self.dll.niHSDIO_Abort(
                self.handle
            )
        )
        # Set self._status to "Idle" independent on op_status
        self._status = 0

        return op_status

    # ================================================================
    # Hardware settings and basic technical methods
    # ================================================================

    # Hardware settings ==============================================

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        return self._get_attribute_real64(NIConst.NIHSDIO_ATTR_SAMPLE_CLOCK_RATE)

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """

        # Sanity check
        constraints = self.get_constraints()
        if sample_rate > constraints.sample_rate.max:
            self.log.warn('set_sample_rate({0} MHz): the requested value exceeds hardware constraint max={1} MHz.\n'
                          'The max possible value will be set instead.'
                          ''.format(sample_rate/1e6, constraints.sample_rate.max/1e6))
            sample_rate = constraints.sample_rate.max
        elif sample_rate < constraints.sample_rate.min:
            self.log.warn('set_sample_rate({0}): the requested value is below the hardware constraint min={1} Hz.\n'
                          'The min possible value will be set instead.'
                          ''.format(sample_rate, constraints.sample_rate.min))
            sample_rate = constraints.sample_rate.min

        # Call DLL function niHSDIO_ConfigureSampleClock()
        # Currently, the onboard clock is used as the sample clock source
        self._er_chk(
            self.dll.niHSDIO_ConfigureSampleClock(
                self.handle,                                # ViSession vi
                NIConst.NIHSDIO_VAL_ON_BOARD_CLOCK_STR,     # ViConstString clockSource
                NITypes.ViReal64(sample_rate)               # ViReal64 clockRate
            )
        )

        # Return the actual final sample rate
        actual_sample_rate = self.get_sample_rate()
        return actual_sample_rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to peak, i.e. the
                               full amplitude) of a specific channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a specific channel is
                            desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor string
                               (i.e. 'a_ch1') and items being the values for those channels.
                               Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.

        Note: Do not return a saved amplitude and/or offset value but instead retrieve the current
              amplitude and/or offset directly from the device.

        If nothing (or None) is passed then the levels of all channels will be returned. If no
        analog channels are present in the device, return just empty dicts.

        Example of a possible input:
            amplitude = ['a_ch1', 'a_ch4'], offset = None
        to obtain the amplitude of channel 1 and 4 and the offset of all channels
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch2': 0.0, 'a_ch3': 1.0, 'a_ch4': 0.0}
        """

        self.log.warn('get_analog_level(): NI-HSDIO does not have analog outputs. ({}, {}) was returned.')
        return {}, {}

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s).

        @param dict amplitude: dictionary, with key being the channel descriptor string
                               (i.e. 'a_ch1', 'a_ch2') and items being the amplitude values
                               (in Volt peak to peak, i.e. the full amplitude) for the desired
                               channel.
        @param dict offset: dictionary, with key being the channel descriptor string
                            (i.e. 'a_ch1', 'a_ch2') and items being the offset values
                            (in absolute volt) for the desired channel.

        @return (dict, dict): tuple of two dicts with the actual set values for amplitude and
                              offset for ALL channels.

        If nothing is passed then the command will return the current amplitudes/offsets.

        Note: After setting the amplitude and/or offset values of the device, use the actual set
              return values for further processing.
        """

        self.log.warn('set_analog_level(): NI-HSDIO does not have analog outputs. ({}, {}) was returned.')
        return {}, {}

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. First dict - low level values, second one - high level values.
                               Both low and high value of a channel is denoted in volts.


        If nothing (or None) is passed then the levels of all channels are being returned.
        If no digital channels are present, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {'d_ch1': 1.0, 'd_ch2': 1.0, ..., 'd_ch31': 1.0}
        Since no high request was performed, the high values for ALL channels are returned (here 31).
        """

        low_val = {}
        high_val = {}

        all_channels = self._get_all_digital_channels()

        if low is None:
            low = all_channels
        if high is None:
            high = all_channels

        # get low levels
        for chnl in low:
            if chnl not in all_channels:
                self.log.warn('Channel "{0}" is not available in NI HSDIO card.\n'
                              'Get low level request is ignored for this entry.'.format(chnl))
                continue

            low_val[chnl] = float(
                self._get_attribute_real64(NIConst.NIHSDIO_ATTR_DATA_VOLTAGE_LOW_LEVEL, chnl_name=chnl)
            )

        # get high levels
        for chnl in high:
            if chnl not in all_channels:
                self.log.warn('Channel "{0}" is not available in NI HSDIO card.\n'
                              'Get high level request is ignored for this entry.'.format(chnl))
                continue

            high_val[chnl] = float(
                self._get_attribute_real64(NIConst.NIHSDIO_ATTR_DATA_VOLTAGE_HIGH_LEVEL, chnl_name=chnl)
            )

        return low_val, high_val

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.
        """

        # 654[1,2,4,5] support only discrete voltage families. Only 6547 and 6548 allow select from some range.

        # FIXME: channels cannot have different voltage families
        # FIXME: if one attempts to assign different levels, DLL gives the following error:
        # FIXME:                            Property must have the same value for all channels on this device.
        # TODO: modify the logic below to accept only discrete set of logic families, once for all channels
        # TODO: modify GUI to don't apply the settings to each separate channel

        if low is None:
            low = {}
        if high is None:
            high = {}

        # Sanity checks
        all_channels = self._get_all_digital_channels()
        constraints = self.get_constraints()

        # Low level [the only allowed value is 0]
        for chnl in low:
            # Sanity checks:
            # -- Check that chnl is a valid channel identifier
            if chnl not in all_channels:
                self.log.warn('Channel "{0}" is not available in NI HSDIO card.\n'
                              'Set low level request is ignored for this entry.'.format(chnl))
                continue
            # -- Check that low[chnl] is 0.0 - the only allowed low value for any NI HSDIO card
            # The form of this check is kept general just to allow for possible extensions
            if low[chnl] > constraints.d_ch_low.max:
                self.log.warn('set_digital_level({0}_low = {1}): '
                              'the requested value exceeds the hardware constraint max={2} V.\n'
                              'The max possible value will be set instead.'
                              ''.format(chnl, low[chnl], constraints.d_ch_low.max))
                low[chnl] = constraints.d_ch_low.max

            if low[chnl] < constraints.d_ch_low.min:
                self.log.warn('set_digital_level({0}_low = {1}): '
                              'the requested value is below the hardware constraint min={2} V.\n'
                              'The min possible value will be set instead.'
                              ''.format(chnl, low[chnl], constraints.d_ch_low.min))
                low[chnl] = constraints.d_ch_low.min

            # Apply new value
                # No function call is performed here since 0.0 is the only available value for low level

        # High level [only a discrete set of values constraints.d_ch_high.list is allowed]
        # TODO: The only exceptions are 6547 and 6548 cards, where the high level can be varied in a certain interval.
        # TODO: to use these cards one needs to modify the check below to use constraints.d_ch_high.min/max
        for chnl in high:
            # Sanity checks:
            # -- Check that chnl is a valid channel identifier
            if chnl not in all_channels:
                self.log.warn('set_digital_level(): channel "{0}" is not available in NI HSDIO card.\n'
                              'Set high level request is ignored for this entry.'.format(chnl))
                continue
            # -- Check that high[chnl] is one of the allowed voltage levels, otherwise replace with the nearest one.
            if high[chnl] not in constraints.d_ch_high.list:
                new_value = self.find_nearest(array=constraints.d_ch_high.list, value=high[chnl])
                self.log.warn('set_digital_level({0}_high = {1}): '
                              'the requested value does not match any of the possible values: {2} V.\n'
                              'The closest value {3} V will be set instead.'
                              ''.format(chnl, high[chnl], constraints.d_ch_high.list, new_value))
                high[chnl] = new_value

            # Prepare channel number string in C-string format
            chnl_numb_string = chnl.rsplit('_ch', 1)[1]
            chnl_numb_string = NITypes.ViString(chnl_numb_string.encode('ascii'))

            # Apply new value
            self._er_chk(
                self.dll.niHSDIO_ConfigureDataVoltageCustomLevels(
                    self.handle,                    # ViSession vi
                    chnl_numb_string,               # ViConstString channelList
                    NITypes.ViReal64(0),            # ViReal64 lowLevel
                    NITypes.ViReal64(high[chnl])    # ViReal64 highLevel
                )
            )

        return self.get_digital_level()

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.
                       In the case of error in the DLL function call, {'d_ch1': False,..., 'd_ch31': False} is returned.

        In NI HSDIO, channel can be configured to static input/output or dynamic input/output.
        For generation purposes, Active channel = Dynamic channel,
        so this function actually returns the list of channels, which are configured to Dynamic mode

        Example for an possible input (order is not important):
            ch = ['d_ch1', 'd_ch2', 'd_ch5', 'd_ch10', 'd_ch12']
        then the output might look like
            {'d_ch1': True, 'd_ch2': False, 'd_ch5': False, 'd_ch10': True, 'd_ch12': False}

        If no parameter (or None) is passed to this method all channel states will be returned.
        """

        # Obtain list of channels, configured to dynamic output mode
        # -- get raw string attribute (should have the following form: '0,1,2,4,10,3,5')
        raw_dynamic_chnl_str = self._get_attribute_string(NIConst.NIHSDIO_ATTR_DYNAMIC_CHANNELS)
        # -- extract channel number strings ('0', '1', ...) and store them in a list
        dynamic_chnl_numb_list = re.findall(r'\d+', raw_dynamic_chnl_str)
        # -- prepend 'd_ch' to each entry ('1' -> 'd_ch1')
        dynamic_chnl_list = ['d_ch' + chnl_numb_str for chnl_numb_str in dynamic_chnl_numb_list]

        # Construct the channel state dictionary for all requested channels

        # -- construct the requested list of channels
        all_channels = self._get_all_digital_channels()
        if ch is None:
            reqst_chnl_list = all_channels
        else:
            reqst_chnl_list = ch

        # -- build chnl_state_dict to be returned
        chnl_state_dict = {}
        for chnl in reqst_chnl_list:
            # Sanity check: chnl is a valid channel identifier
            if chnl not in all_channels:
                self.log.warn('get_active_channels({0}): invalid channel identifier. Ignored this entry.'.format(chnl))
                continue

            # create new entry {'chnl': True/False} in chnl_state_dict
            if chnl in dynamic_chnl_list:
                chnl_state_dict[chnl] = True
            else:
                chnl_state_dict[chnl] = False

        return chnl_state_dict

    def set_active_channels(self, ch=None):
        """
        Set the active/inactive channels for the pulse generator hardware.
        The state of ALL available channels will be returned (True: active, False: inactive).
        The actually set and returned channel activation must be part of the available
        activation_configs in the constraints.
        You can also activate/deactivate subsets of available channels but the resulting
        activation_config must still be valid according to the constraints.
        If the resulting set of active channels can not be found in the available
        activation_configs, the channel states must remain unchanged.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL channels

        If nothing is passed then the command will simply return the unchanged current state.


        Example for possible input:
            ch={'d_ch1': False, 'd_ch2': True, 'd_ch3': True, 'd_ch4': True}
        to activate channel d_ch2, 3d_ch and d_ch4 and to deactivate channel d_ch1.
        All other available channels will remain unchanged.
        """

        if ch is None:
            # No argument passed: do not change anything
            return self.get_active_channels()

        all_channels = self._get_all_digital_channels()
        chnl_state_dict = self.get_active_channels(all_channels)

        # Prepare the new version of chnl_state_dict, by modifying the channels mentioned in ch dictionary
        for chnl in ch:
            # Sanity check: chnl is a valid channel identifier
            if chnl not in all_channels:
                self.log.warn('set_active_channels({0}): invalid channel identifier. Ignored this entry.'.format(chnl))
                continue

            # Modify channel states according to the given ch dictionary
            #   No sanity check against self.get_constraints().activation_config is performed here
            #   because for NI HSDIO cards any set of channels is a valid configuration
            chnl_state_dict[chnl] = ch[chnl]

        # Prepare a NITypes.ViString containing the list of channels, which should be active
        active_chnl_string = ''
        # -- write-in numbers of all channels, which should be active
        for chnl in all_channels:
            if chnl_state_dict[chnl]:
                # add ',' to separate from the previous entry
                active_chnl_string += ','
                # append channel number to the string
                active_chnl_string += chnl.rsplit('_ch', 1)[1]
        # -- remove leading ','
        active_chnl_string = active_chnl_string[1:]
        # -- convert to ViString format
        active_chnl_string = NITypes.ViString(active_chnl_string.encode('ascii'))

        # Call DLL function to apply the new set of dynamic channels
        self._er_chk(
            self.dll.niHSDIO_AssignDynamicChannels(
                self.handle,
                active_chnl_string
            )
        )

        return self.get_active_channels()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        self.log.warn('get_interleave(): NI HSDIO cards do not have interleave. False was returned')
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """
        self.log.warn('set_interleave(): NI HSDIO cards do not have interleave. Nothing was set. False was returned')
        return False

    # Other technical methods =======================================

    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude, total_length_bins,
        channel_config, ...) related to the pulse generator hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to get an impression.
        If still additional constraints are needed, then they have to be added to the
        PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in core.util.interfaces.
        Essentially it contains min/max values as well as min step size, default value and unit of
        the parameter.

        PulserConstraints.activation_config differs, since it contain the channel
        configuration/activation information of the form:
            {<descriptor_str>: <channel_set>,
             <descriptor_str>: <channel_set>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
        sequence mode) just leave it out so that the default is used (only zeros).


        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_conf = OrderedDict()
        activation_conf['yourconf'] = {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4'}
        activation_conf['different_conf'] = {'a_ch1', 'd_ch1', 'd_ch2'}
        activation_conf['something_else'] = {'a_ch2', 'd_ch3', 'd_ch4'}
        constraints.activation_config = activation_conf
        """
        constraints = PulserConstraintsList()

        constraints.sample_rate.min = 48
        constraints.sample_rate.max = 100e6
        constraints.sample_rate.default = 10e6

        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0

        # FIXME: 654[1,2,4,5] support only discrete voltage families. Only 6547 and 6548 allow select from some range.
        constraints.d_ch_high.list = [1.8, 2.5, 3.3]
        constraints.d_ch_high.min = min(constraints.d_ch_high.list)
        constraints.d_ch_high.max = max(constraints.d_ch_high.list)
        constraints.d_ch_high.step = 0.0
        constraints.d_ch_high.default = max(constraints.d_ch_high.list)

        constraints.waveform_length.min = 2
        constraints.waveform_length.step = 2
        constraints.waveform_length.default = 2
        constraints.waveform_length.max = 64800000

        # constraints.waveform_num.min = 1
        # constraints.waveform_num.max = 32000
        # constraints.waveform_num.step = 1
        # constraints.waveform_num.default = 1
        #
        # constraints.sequence_num.min = 1
        # constraints.sequence_num.max = 16000
        # constraints.sequence_num.step = 1
        # constraints.sequence_num.default = 1
        #
        # constraints.subsequence_num.min = 1
        # constraints.subsequence_num.max = 8000
        # constraints.subsequence_num.step = 1
        # constraints.subsequence_num.default = 1
        #
        # # If sequencer mode is available then these should be specified
        # constraints.repetitions.min = 1
        # constraints.repetitions.max = 16777216
        # constraints.repetitions.step = 1
        # constraints.repetitions.default = 1
        #
        # constraints.sequence_steps.min = 0
        # constraints.sequence_steps.max = 8000
        # constraints.sequence_steps.step = 1
        # constraints.sequence_steps.default = 0

        # Here all possible channel configurations are stated.
        # Different can be customary chosen names for the different configurations.
        # the identifiers 'd_ch0', 'd_ch1', ..., 'd_ch31' are channel names.
        # For NI HSDIO card, any set of active channels is a valid configuration,
        # but 'all' is the only one actually used in practice. That is why only 'all' is included below.
        activation_config = OrderedDict()
        # All channels activated
        activation_config['all'] = {'d_ch{0}'.format(i) for i in range(32)}
        constraints.activation_config = activation_config

        return constraints
        pass

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.

        Purpose explanation:
        get_status()[0] is called by sequence_generator_logic (only, no other logic modules use it)
                        before applying any setting changes to make sure that the pulser is not running right now.

        Returned 0 means the pulser is idle and it's safe to apply new settings;
        Positive values mean different states when pusler is running - no changes should be made in this case;
        Negative values mean communication error - connection to instrument lost, for example.
        """

        # Didn't find any way to get actual status directly (didn't find any proper DLL function and attributes)
        # That is why will use a private variable self._status to keep track of it manually

        # FIXME: if generation mode is FINITE, the pulser will finish generation and will return to idle state,
        # FIXME: but self._states will still be 1.

        # TODO: may be it is possible to get the status directly by some trick (request something state-depended)

        status_dict = {
            0: 'NI HSDIO card is idle',
            1: 'NI HSDIO card is running',
            -1: 'NI HSDIO: communication error'
        }

        status = copy.deepcopy(self._status)
        return status, status_dict

    def get_mode(self):
        """

        :return: (str) "W" - Waveform, "S" - Scripted, empty string in the case of error
        """

        mode_id = self._get_attribute_int32(attr_id=NIConst.NIHSDIO_ATTR_GENERATION_MODE)

        if mode_id == NIConst.NIHSDIO_VAL_WAVEFORM.value:
            gen_mode = 'W'
        elif mode_id == NIConst.NIHSDIO_VAL_SCRIPTED.value:
            gen_mode = 'S'
        elif mode_id == -1:
            self.log.error('get_mode(): self._get_attribute_int32(NIHSDIO_ATTR_GENERATION_MODE) call failed.')
            gen_mode = ''
        else:
            self.log.error('get_mode(): self._get_attribute_int32(NIHSDIO_ATTR_GENERATION_MODE) '
                           'returned unknown mode_id = {0}'.format(mode_id))
            gen_mode = ''

        return gen_mode

    def set_mode(self, gen_mode_string):
        """

        :param gen_mode_string: (str) "W" - Waveform, "S" - Scripted
        :return: actual run mode string ("W"/"S")
        """

        if gen_mode_string == 'W':
            run_mode = NIConst.NIHSDIO_VAL_WAVEFORM
        elif gen_mode_string == 'S':
            run_mode = NIConst.NIHSDIO_VAL_SCRIPTED
        else:
            self.log.error('set_mode({0}): invalid argument. Valid values: "W" - Waveform, "S" - scripted.\n'
                           'Run mode was not changed. Actual run mode string was returned.'.format(gen_mode_string))
            return self.get_mode()

        # Call DLL function
        self._er_chk(
            self.dll.niHSDIO_ConfigureGenerationMode(
                self.handle,  # ViSession vi
                run_mode      # ViInt32 generationMode
            )
        )

        # Return actual run mode
        return self.get_mode()

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """

        op_status = self._er_chk(
            self.dll.niHSDIO_reset(self.handle)
        )

        # Empty the waveform and sequence record keeping lists
        self._wfm_list = []
        self._script_list = []

        # Set status to "Idle"
        self._status = 0

        return op_status

    @staticmethod
    def _get_all_digital_channels():
        """
        Helper method to return a sorted list of all technically available channel descriptors

        @return list: Sorted list of channels ['d_ch0', 'd_ch1', ..., 'd_ch31']
        """
        available_channels = ['d_ch{}'.format(i) for i in range(32)]

        return available_channels

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        # NI HSDIO cards do not have Sequence mode. Instead, Script mode can be used.
        # To avoid problems with the above logic layers, which want to use Sequence,
        # one pretends that the card is just a plain waveform generator and False is returned here.

        # TODO: Reconsider this, once the Script methods are implemented:
        # TODO:          may be is makes sense to return True and substitute some Sequence features by Script

        return False

    @staticmethod
    def find_nearest(array, value):
        """
        Returns the array element closest to the given value

        This function is used in self.set_digital_level() to find the nearest allowed high level voltage from
        constraints.d_ch_high.list if the requested value does not match any of them.

        :param array:
        :param value:
        :return:
        """
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return array[idx]

    # Wrappers for C DLL helper functions ===================================

    def _er_chk(self, error_code):
        # C:\Program Files\National Instruments\Shared\Errors\English\IVI-errors.txt

        if error_code == 0:
            op_status = 0
        else:
            op_status = -1

            # Create buffer for DLL function to output the error message string
            msg_buf = ctypes.create_string_buffer(256)

            # Call DLL function to generate readable error message
            self.dll.niHSDIO_error_message(
                self.handle,                   # ViSession vi
                NITypes.ViStatus(error_code),  # ViStatus errorCode
                msg_buf                        # ViChar errorMessage[256]
            )
            self.log.error(msg_buf.value.decode('ascii'))

        return op_status

    def _get_attribute_int32(self, attr_id, chnl_name=None):
        """

        :param attr_id:
        :param chnl_name:
        :return: (int) obtained value in the case of success, -1 in the case of error
        """

        # Create buffer for niHSDIO_GetAttribute to store the result
        buf = NITypes.ViInt32()

        # Process channel identifier string (used to request channel-agnostic/-specific attributes)
        if chnl_name is None:
            chnl_numb_string = NIConst.VI_NULL
        else:
            # Extract number from chnl_name ('d_ch1' -> '1')
            chnl_numb_string = chnl_name.rsplit('_ch', 1)[1]
            # Convert into C-string
            chnl_numb_string = ctypes.c_char_p(chnl_numb_string.encode('ascii'))

        # Call DLL function
        # DLL normally handles all "moderate" errors and returns error code, which is being analyzed by self._er_chk
        # "try" handles OSError when the DLL function fails completely and isn't able to handle the error by itself
        try:
            op_status = self._er_chk(
                self.dll.niHSDIO_GetAttributeViInt32(
                    self.handle,        # ViSession vi
                    chnl_numb_string,   # ViConstString channelName
                    attr_id,            # ViAttr attribute
                    ctypes.byref(buf)   # ViInt32 *value
                )
            )
        except OSError:
            self.log.error('_get_attribute_int32(): OSError, DLL function call failed')
            return -1

        # Check for "moderate" error and return the result as Python-int
        if op_status == 0:
            return buf.value
        else:
            return -1

    def _get_attribute_string(self, attr_id, chnl_name=None):
        """

        :param attr_id:
        :param chnl_name:
        :return: (str) obtained string, empty string in the case of error.
        """

        # Create buffer for niHSDIO_GetAttribute to store the result
        buf_size = 1024  # Buffer size of 1024 was chosen for no specific reason. Increase if needed.
        buf = ctypes.create_string_buffer(buf_size)

        # Process channel identifier string (used to request channel-agnostic/-specific attributes)
        if chnl_name is None:
            chnl_numb_string = NIConst.VI_NULL
        else:
            # Extract number from chnl_name ('d_ch1' -> '1')
            chnl_numb_string = chnl_name.rsplit('_ch', 1)[1]
            # Convert into C-string
            chnl_numb_string = ctypes.c_char_p(chnl_numb_string.encode('ascii'))

        # Call DLL function
        # DLL normally handles all "moderate" errors and returns error code, which is being analyzed by self._er_chk
        # "try" handles OSError when the DLL function fails completely and isn't able to handle the error by itself
        try:
            op_status = self._er_chk(
                self.dll.niHSDIO_GetAttributeViString(
                    self.handle,                # ViSession vi
                    chnl_numb_string,           # ViConstString channelName
                    attr_id,                    # ViAttr attribute
                    NITypes.ViInt32(buf_size),  # ViInt32 bufSize
                    buf                         # ViChar value[]
                )
            )
        except OSError:
            self.log.error('_get_attribute_string(): OSError, DLL function call failed')
            return ''

        # Check for "moderate" error and return the result as Python-string
        if op_status == 0:
            return buf.value.decode('ascii')
        else:
            return ''

    def _get_attribute_real64(self, attr_id, chnl_name=None):
        """

        :param attr_id:
        :param chnl_name:
        :return: (float) obtained value, -1.0 in the case of error
        """

        # Create buffer for niHSDIO_GetAttribute to store the result
        buf = NITypes.ViReal64()

        # Process channel identifier string (used to request channel-agnostic/-specific attributes)
        if chnl_name is None:
            chnl_numb_string = NIConst.VI_NULL
        else:
            # Extract number from chnl_name ('d_ch1' -> '1')
            chnl_numb_string = chnl_name.rsplit('_ch', 1)[1]
            # Convert into C-string
            chnl_numb_string = ctypes.c_char_p(chnl_numb_string.encode('ascii'))

        # Call DLL function
        # DLL normally handles all "moderate" errors and returns error code, which is being analyzed by self._er_chk
        # "try" handles OSError when the DLL function fails completely and isn't able to handle the error by itself
        try:
            op_status = self._er_chk(
                self.dll.niHSDIO_GetAttributeViReal64(
                    self.handle,        # ViSession vi
                    chnl_numb_string,   # ViConstString channelName
                    attr_id,            # ViAttr attribute
                    ctypes.byref(buf)   # ViReal64 *value
                )
            )
        except OSError:
            self.log.error('_get_attribute_real64(): OSError, DLL function call failed')
            return -1.0

        # Check for "moderate" error and return the results as Python-float
        if op_status == 0:
            return buf.value
        else:
            return -1.0

    # ================================================================
    # Waveform and Sequence Generation
    # ================================================================

    # Waveform Generation ============================================

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk,
                       total_number_of_samples):
        """
        Write a new waveform or append samples to an already existing waveform on the device memory.
        The flags is_first_chunk and is_last_chunk can be used as indicator if a new waveform should
        be created or if the write process to a waveform should be terminated.

        NOTE: All sample arrays in analog_samples and digital_samples must be of equal length!

        @param str name: the name of the waveform to be created/append to
        @param dict analog_samples: keys are the generic analog channel names (i.e. 'a_ch1') and
                                    values are 1D numpy arrays of type float32 containing the
                                    voltage samples.
        @param dict digital_samples: keys are the generic digital channel names (i.e. 'd_ch1') and
                                     values are 1D numpy arrays of type bool containing the marker
                                     states.
        @param bool is_first_chunk: Flag indicating if it is the first chunk to write.
                                    If True this method will create a new empty waveform.
                                    If False the samples are appended to the existing waveform.
        @param bool is_last_chunk:  Flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.
        @param int total_number_of_samples: The number of sample points for the entire waveform
                                            (not only the currently written chunk)

        @return (int, list): Number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """
        # pass

        # COMMENT ON CHUNK-WISE WRITING
        # This method is called by sequence_generator_logic.sample_pulse_block_ensemble() method.
        #
        # In principle, to avoid using large memory, it should be called multiple times to write the entire
        # waveform in smaller chunks.
        #
        # Practically this is not needed: test on Lukin-SiV showed that a pulse block ensemble of ~1e9 samples
        # (70 ms with 10 GHz sample rate) still can be accommodated in memory (x10 already causes MemoryError) which
        # is significantly larger than any reasonable waveform and even total card's memory (max 256 Mbytes total)
        #
        # Chunk-wise loading with NI HSDIO can be implemented by niHSDIO_AllocateNamedWaveform() and then multiple
        # calls of niHSDIO_WriteNamedWaveformU32(). But when using manual memory allocation, the chunk size must be
        # an integer multiple of 32 bit (or 64 bit, for some cards), which would require some extra logic in
        # sequence_generator_logic.
        #
        # Finally, the default.cfg says: "#overhead_bytes: 4294967296  # Not properly implemented yet",
        # so this functionality is not yet implemented
        #
        # In this way, it doesn't make sense to implement chunk-wise write in this method.
        #
        # Without manual memory allocation, sequential calls of niHSDIO_WriteNamedWaveformU32() with the same wfm_name
        # lead to overwriting of the existing waveform and, eventually, to errors. To prevent this,
        # the method will generate error if is_first_chunk or is_last_chunk are not True.
        #
        # To ensure that sequence_generator_logic.sample_pulse_block_ensemble() writes the entire waveform
        # in a single chunk, specify the following in the config: "overhead_bytes: 0" (which is the default)

        constraints = self.get_constraints()
        # Sanity checks:
        #  -- only "entire waveform write" is currently supported
        if not is_first_chunk or not is_last_chunk:
            self.log.error('write_waveform(): chunk-write is not implemented, '
                           'current code can only write the entire waveform as a whole. \n'
                           'The passed arguments [is_first_chunk={0}, is_last_chunk={1}] indicate that '
                           'sequence_generator_logic attempts to write in chunks. \n'
                           'To switch this mode off, specify "overhead_bytes: 0" in sequence_generator_logic config.'
                           ''.format(is_first_chunk, is_last_chunk))
            return -1, []

        #  -- all arrays have same length of total_number_of_samples
        for chnl_name in digital_samples.keys():
            if len(digital_samples[chnl_name]) != total_number_of_samples:
                self.log.error('write_waveform(): waveform {0} for channel {1} has length of {2}, '
                               'which is different from the claimed total_number_of_samples = {3}'
                               ''.format(name, chnl_name, len(digital_samples[chnl_name]), total_number_of_samples))
                return -1, []

        #  -- total_number_of_samples is between min and max waveform length
        if total_number_of_samples > constraints.waveform_length.max:
            self.log.error('write_waveform(): waveform {0} has length of {1}, which exceeds hardware-max of {2}'
                           ''.format(name, total_number_of_samples, constraints.waveform_length.max))
            return -1, []
        elif total_number_of_samples < constraints.waveform_length.min:
            self.log.error('write_waveform(): waveform {0} has length of {1}, which is smaller than hardware-min of {2}'
                           ''.format(name, total_number_of_samples, constraints.waveform_length.min))
            return -1, []

        #  -- only data_width=32 write is currently implemented (DLL function niHSDIO_WriteNamedWaveformU32)
        hardware_data_width = 8 * self._get_attribute_int32(NIConst.NIHSDIO_ATTR_DATA_WIDTH)
        if hardware_data_width != 32:
            self.log.error('write_waveform(): the card you use has data_width = {0} bits. \n'
                           'The method was written assuming 32-bit width and have to be modified for your card.'
                           'Rewrite sample_ar construction part and use niHSDIO_WriteNamedWaveformU{1}() DLL function'
                           ''.format(hardware_data_width, hardware_data_width))
            return -1, []

        #  -- if wfm length is not an integer multiple of hardware-defined step,
        #     the array will be appended with extension_len of "all-off" samples (uint32 zero) at the end
        extension_len = total_number_of_samples % constraints.waveform_length.step
        if extension_len != 0:
            self.log.warn(
                'write_waveform(): passed waveform has length of {0}, which is not an integer multiple of '
                'hardware-defined step {1}. \n'
                'To compensate this mismatch, the waveform will be appended with {2} "all-off" samples at the end'
                ''.format(total_number_of_samples, constraints.waveform_length.step, extension_len))

        # ================================
        # Construct sample array
        #  -- create blank array
        sample_ar = np.zeros(total_number_of_samples + extension_len, dtype=np.uint32)

        #  -- iterate through each sample
        #     calculate the uint32 where bits represent individual channels, LSB = d_ch0, ..., MSB = d_ch31
        for sample_index in range(total_number_of_samples):
            # Iterate through each channel name
            # Introduce changes only to the bits of channels, which are mentioned in digital_samples.keys()
            # Other channel bits will have default 0
            for chnl_name in digital_samples.keys():
                if digital_samples[chnl_name][sample_index]:
                    # Place 1 at the position of the channel bit
                    chnl_bit_num = int(chnl_name.rsplit('_ch', 1)[1])
                    sample_ar[sample_index] += (1 << chnl_bit_num)
                else:
                    # No need to change the bit: 0 is the default
                    continue
        # All samples in [total_number_of_samples, total_number_of_samples + extension_len - 1] have all bits 0

        # Delete digital_samples since now the whole waveform is contained in sample_ar
        del digital_samples

        # Delete previous wfm_name=name if it is present in the device memory
        if name in self.get_waveform_names():
            deleted_wfm_list = self.delete_waveform(name)
            if name not in deleted_wfm_list:
                self.log.error('write_waveform(): failed to delete "{0}" waveform from device memory'
                               ''.format(name))
                return -1, []

        # Write sample_ar to the device memory
        #  -- create C-pointer to sample_ar using numpy.ndarray.ctypes attribute
        sample_arr_ptr = sample_ar.ctypes.data_as(ctypes.POINTER(NITypes.ViUInt32))
        #  -- call DLL function
        op_status = self._er_chk(
            self.dll.niHSDIO_WriteNamedWaveformU32(
                self.handle,                                                # ViSession vi
                NITypes.ViConstString(name.encode('ascii')),                # ViConstString waveformName
                NITypes.ViInt32(total_number_of_samples + extension_len),   # ViInt32 samplesToWrite
                sample_arr_ptr                                              # ViUInt32 data[]
            )
        )

        # Add name to the list of available waveforms
        if op_status == 0:
            self._wfm_list.append(name)

        # Return
        if op_status == 0:
            return total_number_of_samples, [name]
        else:
            return -1, []

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names is given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names if given,
                                    the channel association will be invoked from
                                    the channel suffix '_ch1', '_ch2' etc. A
                                    possible configuration can be e.g.

                                        ['rabi_ch1', 'rabi_ch2', 'rabi_ch3']

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the waveform
        from the device workspace into the channel. For a device without mass
        memory, this will make the waveform/pattern that has been previously
        written with self.write_waveform ready to play.

        Please note that the channel index used here is not to be confused with the number suffix
        in the generic channel descriptors (i.e. 'd_ch1', 'a_ch1'). The channel index used here is
        highly hardware specific and corresponds to a collection of digital and analog channels
        being associated to a SINGLE waveform asset.
        """

        # FIXME: figure out the format of the input load_dict and modify logic below

        self.log.debug('The load_dict passed: {}'.format(load_dict))
        wfm_name = load_dict[0]

        # Sanity check: waveform is present in the device memory
        if wfm_name not in self.get_waveform_names():
            self.log.error('load_waveform({0}): this waveform is not present in the device memory'.format(wfm_name))
            return {}

        self._er_chk(
            self.dll.niHSDIO_ConfigureWaveformToGenerate(
                self.handle,                                     # ViSession vi
                NITypes.ViConstString(wfm_name.encode('ascii'))  # ViConstString waveformName
            )
        )

        # Set Waveform generation mode
        self.set_mode(gen_mode_string='W')

        # # Set Waveform repetition to "play once"
        # self.set_waveform_repeat(1)

        loaded_wfm = self._get_attribute_string(NIConst.NIHSDIO_ATTR_WAVEFORM_TO_GENERATE)
        return {'d_ch0': loaded_wfm}

    # Sequence Generation ============================================

    # NI PXI(PCI)-654X cards do not support Sequence generation mode. That is why the methods in this section
    # are just place holders to avoid errors.
    # Instead, the cards have script functionality. Corresponding methods are in the "Script Generation" section below.

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: list containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)

        EXPLANATIONS

        sequence_parameters = [
            (('stp1_wfm_ch1', 'stp1_wfm_ch2'), {'repetitions': #, 'wait_for': #, 'go_to': #, 'event_jump_to': #}),
            (('stp2_wfm_ch1', 'stp2_wfm_ch2'), {'repetitions': #, 'wait_for': #, 'go_to': #, 'event_jump_to': #}),
        ]

        Meaning of the parameter dictionary entries:
        'repetitions': -1 -- infinite; 0 and 1 -- once; 2 -- twice; ...
        'wait_for': 'ON' or 'OFF'
        'go_to': positive integer - number of sequence element to go to after completing palying elem_num,
                 negative integer and 0 - disable GoTo
        'event_jump_to': positive int -- jump destination; 0 -- NEXT; -1 -- events ignored, no jump from this element

        Usage example:
        seq_param_list = [
            (('test1_ch1', 'test1_ch2'), {'repetitions': -1, 'wait_for': 'OFF', 'go_to': 1, 'event_jump_to': 0}),
            (('test2_ch1', 'test2_ch2'), {'repetitions': 100, 'wait_for': 'ON', 'go_to': 1, 'event_jump_to': 1}),
        ]
        awg_instance_name.write_sequence('sequence_name', seq_param_list)

        """

        self.log.warn('write_sequence(): NI HSDIO card does not support Sequence mode. Use Script mode instead.')
        return 0

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list sequence_name: a dictionary with keys being one of the available channel
                                        index and values being the name of the already written
                                        waveform to load into the channel.
                                        Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                    {1: rabi_ch2, 2: rabi_ch1}
                                        If just a list of waveform names if given, the channel
                                        association will be invoked from the channel
                                        suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        self.log.warn('load_sequence(): NI HSDIO card does not support Sequence mode. Use Script mode instead.')
        return {}

    # Waveform and sequence technical ================================

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        return copy.deepcopy(self._wfm_list)

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        self.log.warn('get_sequence_names(): NI HSDIO card does not support Sequence mode. Use Script mode instead.')
        return []

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str|list waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """

        # Handle string and list input formats
        if isinstance(waveform_name, list):
            rm_wfm_list = waveform_name
        elif isinstance(waveform_name, str):
            rm_wfm_list = [waveform_name]
        else:
            self.log.error('delete_waveform({0}) - unknown argument type: only string or list of strings are acceptable'
                           ''.format(waveform_name))
            return []

        # List of deleted waveforms to be returned
        deleted_wfm_list = []
        # List of all waveforms in the memory
        avail_wfm_list = self.get_waveform_names()

        for wfm_name in rm_wfm_list:
            # Sanity check: wfm_name is present in the memory
            if wfm_name not in avail_wfm_list:
                self.log.error('delete_waveform({0}): this waveform is not present in the device memory'
                               ''.format(wfm_name))
                continue

            # Call DLL function
            op_status = self._er_chk(
                self.dll.niHSDIO_DeleteNamedWaveform(
                    self.handle,                                       # ViSession vi
                    NITypes.ViConstString(wfm_name.encode('ascii'))    # ViConstString waveformName
                )
            )
            if op_status == 0:
                # Add wfm_name to the return list
                deleted_wfm_list.append(wfm_name)
                # Remove wfm_name from list of waveforms in the memory
                self._wfm_list.remove(wfm_name)
            else:
                self.log.error('delete_waveform(): failed to delete waveform "{0}"'.format(wfm_name))

        return deleted_wfm_list

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        self.log.warn('delete_sequence(): NI HSDIO card does not support Sequence mode. Use Script mode instead.')
        return []

    def get_waveform_repeat(self):
        """
        Returns number of repetitions in Waveform generation mode.

        On the hardware level, it is just a pair of attributes NIHSDIO_ATTR_REPEAT_MODE and NIHSDIO_ATTR_REPEAT_COUNT
        which are not bound to any specific waveform.

        :return: (int) repeat mode + number of repetitions:
                    0 - repeat infinitely
                    positive integer - finite, number of reperitions
                    -1 - error
        """
        repeat_mode = self._get_attribute_int32(NIConst.NIHSDIO_ATTR_REPEAT_MODE)

        if repeat_mode == NIConst.NIHSDIO_VAL_CONTINUOUS.value:
            repeat_count = 0
        elif repeat_mode == NIConst.NIHSDIO_VAL_FINITE.value:
            repeat_count = self._get_attribute_int32(NIConst.NIHSDIO_ATTR_REPEAT_COUNT)
        else:
            repeat_count = -1  # if _get_attribute_int32(REPEAT_MODE) failed

        return repeat_count

    def set_waveform_repeat(self, repeat_count):
        """
        Set repeat mode and number of repetitions

        :param repeat_count: (int) repeat mode + number of repetitions:
                    0 - repeat infinitely
                    positive integer - finite, number of repetitions

        :return: (int) actual repeat mode + number of repetitions:
                    0 - repeat infinitely
                    positive integer - finite, number of reperitions
                    -1 - error
        """
        if repeat_count == 0:
            repeat_mode = NIConst.NIHSDIO_VAL_CONTINUOUS
            repeat_count = NIConst.VI_NULL
        elif repeat_count > 0:
            repeat_mode = NIConst.NIHSDIO_VAL_FINITE
        else:
            self.log.error('set_waveform_repeat(repeat_count={0}) invalid argument. \n'
                           'Valid values: 0 - infinite, positive integer - finite'
                           ''.format(repeat_count))
            return -1

        # ViStatus = niHSDIO_ConfigureGenerationRepeat ( ViSession vi, ViInt32 repeatMode, ViInt32 repeatCount);
        self._er_chk(
            self.dll.niHSDIO_ConfigureGenerationRepeat(
                self.handle,  # ViSession vi
                repeat_mode,  # ViInt32 repeatMode
                repeat_count  # ViInt32 repeatCount
            )
        )

        return self.get_waveform_repeat()

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """

        gen_mode = self.get_mode()
        if gen_mode == 'W':
            gen_mode = 'waveform'
            asset_name = self._get_attribute_string(NIConst.NIHSDIO_ATTR_WAVEFORM_TO_GENERATE)
        elif gen_mode == 'S':
            # TODO: in subclass of sequence_generator_logic for NI HSDIO re-implement loaded_asset() to include 'script'
            gen_mode = 'script'
            asset_name = self._get_attribute_string(NIConst.NIHSDIO_ATTR_SCRIPT_TO_GENERATE)
        else:
            gen_mode = ''
            asset_name = ''

        # Construct asset_dict to be returned
        asset_dict = {}

        if asset_name != '':
            all_channels = self._get_all_digital_channels()
            for chnl_name in all_channels:
                # In the case of NI HSDIO there is only one waveform/script asset_name for all channels
                asset_dict[chnl_name] = asset_name + '_' + chnl_name.rsplit('_', 1)[1]

        return asset_dict, gen_mode

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        wfm_list = self.get_waveform_names()
        script_list = self.get_script_names()

        del_wfm_list = self.delete_waveform(wfm_list)
        del_script_list = self.delete_script(script_list)

        if del_wfm_list != wfm_list or del_script_list != script_list:
            self.log.error('clear_all() failed. The following assets are still in the memory:\n'
                           'waveforms: {0}\n'
                           'scripts: {1}'
                           ''.format(self.get_waveform_names(), self.get_script_names()))
            return -1
        else:
            return 0

    # ################################################################
    #                    Beyond PulserInterface
    # ################################################################

    # ================================================================
    # Script Generation
    # ================================================================

    def write_script(self, script_string):

        # Sanity check: script_string is a string
        if not isinstance(script_string, str):
            self.log.error('write_script(): passed argument is not a string')
            return ''

        plain_script_string = script_string.replace('\n', ' ')

        # Try extracting script name
        script_name = plain_script_string.split()[1]

        # Delete previous script_name if it is present in the device memory
        if script_name in self.get_script_names():
            self.delete_script(script_name)

        # Convert into C-string
        c_script_string = NITypes.ViConstString(plain_script_string.encode('ascii'))

        op_status = self._er_chk(
            self.dll.niHSDIO_WriteScript(
                self.handle,     # ViSession vi
                c_script_string  # ViConstString script
            )
        )

        if op_status == 0:
            self._script_list.append(script_name)
            return script_name
        else:
            self.log.error('write_script(): failed to write script "{0}"'.format(script_name))
            return ''

    def load_script(self, script_name):

        # Sanity check: the script is available in the on-board memory
        if script_name not in self.get_script_names():
            self.log.error('load_script(): script {0} is not present in the device memory'.format(script_name))
            return ''

        self._er_chk(
            self.dll.niHSDIO_ConfigureScriptToGenerate(
                self.handle,
                NITypes.ViConstString(script_name.encode('ascii'))
            )
        )

        self.set_mode(gen_mode_string='S')

        loaded_script = self._get_attribute_string(NIConst.NIHSDIO_ATTR_SCRIPT_TO_GENERATE)
        return loaded_script

    # Script technical ===============================================

    def get_script_names(self):
        return copy.deepcopy(self._script_list)

    def delete_script(self, script_name):
        """

        :param script_name: (str|list of strings)
        :return:
        """

        # Handle string and list input formats
        if isinstance(script_name, list):
            rm_script_list = script_name
        elif isinstance(script_name, str):
            rm_script_list = [script_name]
        else:
            self.log.error('delete_script({0}) - unknown argument type: only string or list of strings are acceptable'
                           ''.format(script_name))
            return []

        # List of deleted scripts to be returned
        deleted_script_list = []
        # List of all scripts in the memory
        avail_script_list = self.get_script_names()

        for script_name in rm_script_list:
            # Sanity check: script_name is present in the memory
            if script_name not in avail_script_list:
                self.log.error('delete_script({0}): this script is not present in the device memory'
                               ''.format(script_name))
                continue

            # FIXME: find DLL function to actually delete script
            self._script_list.remove(script_name)
            deleted_script_list.append(script_name)

        return deleted_script_list


class ScalarConstraintList(ScalarConstraint):

    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit='', list=None):
        super().__init__(min=min, max=max, step=step, default=default, unit=unit)

        if list is None:
            self.list = []
        else:
            self.list = list


class PulserConstraintsList(PulserConstraints):

    def __init__(self):
        super().__init__()

        self.d_ch_high = ScalarConstraintList(unit='V')


