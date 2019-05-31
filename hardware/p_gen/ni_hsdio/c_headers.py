import ctypes

# #if defined(LONG_MAX) && (LONG_MAX > 0x7FFFFFFFL)
# typedef unsigned int        ViUInt32;
# typedef _VI_SIGNED int      ViInt32;
# #else
# typedef unsigned long       ViUInt32;
# typedef _VI_SIGNED long     ViInt32;
# #endif


class NITypes:
    ViUInt16 = ctypes.c_ushort  # for ViPUInt16 - use ct.byref()
    ViUInt32 = ctypes.c_uint32
    ViInt32 = ctypes.c_int32

    ViReal64 = ctypes.c_double

    ViBoolean = ViUInt16

    ViChar = ctypes.c_char
    ViPChar = ctypes.c_char_p
    ViString = ViPChar
    ViConstString = ViPChar

    ViAttr = ViUInt32
    ViRsrc = ViString
    ViObject = ViUInt32
    ViSession = ViObject
    ViStatus = ViInt32


class NIConst:
    # ========== Symbolic constants =================
    VI_TRUE = NITypes.ViBoolean(1)
    VI_FALSE = NITypes.ViBoolean(0)
    VI_NULL = NITypes.ViUInt32(0)
    VI_SUCCESS = ctypes.c_long(0)

    NIHSDIO_VAL_ON_BOARD_CLOCK_STR = NITypes.ViConstString(b"OnBoardClock")

    # Attributes
    IVI_ATTR_BASE = 1000000
    IVI_SPECIFIC_PUBLIC_ATTR_BASE = IVI_ATTR_BASE + 150000

    # /***************************************************************************************************
    #  *------------------------------------------ Attribute Defines ------------------------------------*
    #  ***************************************************************************************************/

    # /* IVI Inherent Instrument Attributes */

    # /* Advanced Session Information */

    # /********************************** Instrument-Specific Attributes *********************************/

    # /* Base attributes */
    NIHSDIO_ATTR_DYNAMIC_CHANNELS = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 2)  # /* ViString */
    NIHSDIO_ATTR_STATIC_CHANNELS = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 3)  # /* ViString */

    # /* Device attributes */
    NIHSDIO_ATTR_TOTAL_GENERATION_MEMORY_SIZE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 74)  # / * ViInt32 * /

    # /* Voltage attributes */
    NIHSDIO_ATTR_DATA_VOLTAGE_LOW_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 6)   # ViReal64, channel-based
    NIHSDIO_ATTR_DATA_VOLTAGE_HIGH_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 7)  # ViReal64, channel-based
    NIHSDIO_ATTR_DATA_TERMINATION_VOLTAGE_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 161)  # ViReal64, channel-based
    NIHSDIO_ATTR_DATA_VOLTAGE_RANGE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 163)  # /* ViInt32 */
    NIHSDIO_ATTR_TRIGGER_VOLTAGE_LOW_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 8)   # /* ViReal64 */
    NIHSDIO_ATTR_TRIGGER_VOLTAGE_HIGH_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 9)  # /* ViReal64 */
    NIHSDIO_ATTR_EVENT_VOLTAGE_LOW_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 79)    # /* ViReal64 */
    NIHSDIO_ATTR_EVENT_VOLTAGE_HIGH_LEVEL = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 80)   # /* ViReal64 */

    # /* Channel attributes */

    # /* Clocking attributes */

    # /* Triggers attributes */

    # /* Events attributes */

    # /* Dynamic output attributes */
    NIHSDIO_ATTR_GENERATION_MODE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 25)       # /* ViInt32 */
    NIHSDIO_ATTR_REPEAT_MODE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 26)           # /* ViInt32 */
    NIHSDIO_ATTR_REPEAT_COUNT = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 71)          # /* ViInt32 */
    NIHSDIO_ATTR_WAVEFORM_TO_GENERATE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 27)  # /* ViString */
    NIHSDIO_ATTR_SCRIPT_TO_GENERATE = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 28)    # /* ViString */

    # /* Dynamic input attributes */

    # /* Data Position Delay */

    # /* Data Width */
    NIHSDIO_ATTR_DATA_WIDTH = NITypes.ViAttr(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 108)   # / * ViInt32 * /

    # /* Data Rate Multiplier */

    # /* Supported Data States */

    # /* Synchronization attributes */

    # /* Hardware compare */

    # /* Streaming attributes */

    # /* DirectDMA attributes */

    # /* Bandwidth Governing attributes */

    # /* Power Management attributes */

    # /***************************************************************************************************
    #  *----------------------------------- Attribute Value Defines -------------------------------------*
    #  ***************************************************************************************************/

    # /************************** Instrument specific attribute value definitions ************************/

    # /* Data interpretation */

    # /* Drive type */

    # /* Logic family */

    # /* Data Voltage Range */

    # /* Tristate Mode */

    # /* Digital edge */

    # /* Pattern Match Values */

    # /* Trigger digital pattern trigger when */

    # /* Event polarity */

    # /* Generation mode */
    NIHSDIO_VAL_WAVEFORM = NITypes.ViInt32(14)
    NIHSDIO_VAL_SCRIPTED = NITypes.ViInt32(15)

    # /* Repeat mode */
    NIHSDIO_VAL_FINITE = NITypes.ViInt32(16)
    NIHSDIO_VAL_CONTINUOUS = NITypes.ViInt32(17)

    # /* Initial/Idle State */

    # /* Trigger Types */

    # /* Level Trigger Values */

    # /* Signal Values */

    # /* Terminal Configuration Values */

    # /****** String enum values for signal names *******/
    # #define NIHSDIO_VAL_SCRIPT_TRIGGER0                      "scriptTrigger0"
    # #define NIHSDIO_VAL_SCRIPT_TRIGGER1                      "scriptTrigger1"
    # #define NIHSDIO_VAL_SCRIPT_TRIGGER2                      "scriptTrigger2"
    # #define NIHSDIO_VAL_SCRIPT_TRIGGER3                      "scriptTrigger3"
    # #define NIHSDIO_VAL_MARKER_EVENT0                        "marker0"
    # #define NIHSDIO_VAL_MARKER_EVENT1                        "marker1"
    # #define NIHSDIO_VAL_MARKER_EVENT2                        "marker2"
    # #define NIHSDIO_VAL_MARKER_EVENT3                        "marker3"





    # NIHSDIO_ATTR_DATA_WIDTH = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 108)
    NIHSDIO_ATTR_SAMPLE_CLOCK_SOURCE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 13)  # output type: ViString
    NIHSDIO_ATTR_SAMPLE_CLOCK_RATE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 14)
    NIHSDIO_ATTR_SERIAL_NUMBER = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 96)

    # Generation mode
    # NIHSDIO_VAL_WAVEFORM = NITypes.ViInt32(14)
    # NIHSDIO_VAL_SCRIPTED = NITypes.ViInt32(15)
    # NIHSDIO_ATTR_GENERATION_MODE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 25)  # output type: ViInt32

    # Repeat mode and count (use only for Waveform mode)
    # NIHSDIO_VAL_FINITE = NITypes.ViInt32(16)
    # NIHSDIO_VAL_CONTINUOUS = NITypes.ViInt32(17)
    # NIHSDIO_ATTR_REPEAT_MODE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 26)  # output type: ViInt32
    # NIHSDIO_ATTR_REPEAT_COUNT = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 71)  # output type: ViInt32

    # Waveform/Script to generate
    # NIHSDIO_ATTR_WAVEFORM_TO_GENERATE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 27)  # output type: ViString
    # NIHSDIO_ATTR_SCRIPT_TO_GENERATE = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 28)  # output type: ViString

    # Logic Level Voltage
    NIHSDIO_VAL_5_0V_LOGIC = NITypes.ViInt32(5)
    NIHSDIO_VAL_3_3V_LOGIC = NITypes.ViInt32(6)
    NIHSDIO_VAL_2_5V_LOGIC = NITypes.ViInt32(7)
    NIHSDIO_VAL_1_8V_LOGIC = NITypes.ViInt32(8)
    NIHSDIO_VAL_1_5V_LOGIC = NITypes.ViInt32(80)
    NIHSDIO_VAL_1_2V_LOGIC = NITypes.ViInt32(81)

    # NIHSDIO_ATTR_DATA_VOLTAGE_LOW_LEVEL = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 6)
    # NIHSDIO_ATTR_DATA_VOLTAGE_HIGH_LEVEL = NITypes.ViInt32(IVI_SPECIFIC_PUBLIC_ATTR_BASE + 7)


# ========= Function prototypes =================

def build_c_func_prototypes(ni_hsdio_dll_instance):
    ni_hsdio_dll_instance.niHSDIO_error_message.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_InitGenerationSession.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_AssignDynamicChannels.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureSampleClock.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureDataVoltageLogicFamily.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureDataVoltageCustomLevels.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_GetAttributeViInt32.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_GetAttributeViReal64.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_GetAttributeViString.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_WriteNamedWaveformU32.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_DeleteNamedWaveform.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_WriteScript.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_ConfigureGenerationMode.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureGenerationRepeat.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureWaveformToGenerate.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_ConfigureScriptToGenerate.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_ConfigureDigitalEdgeStartTrigger.restype = NITypes.ViStatus

    ni_hsdio_dll_instance.niHSDIO_Initiate.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_Abort.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_close.restype = NITypes.ViStatus
    ni_hsdio_dll_instance.niHSDIO_reset.restype = NITypes.ViStatus
