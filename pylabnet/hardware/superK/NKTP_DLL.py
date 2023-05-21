# Testing
import ctypes
import os
from ctypes import *
from collections import namedtuple

# Try preloading the OS related DLL, x86 or x64.
# Alternatively copy the correct version into your script folder.

dllFolder = os.environ.get('NKTP_SDK_PATH',r'C:\NKTP_SDK')
if (ctypes.sizeof(ctypes.c_voidp) == 4):
        print('Loading x86 DLL from:', dllFolder + r'\NKTPDLL\x86\NKTPDLL.dll')
        NKTPDLL = ctypes.cdll.LoadLibrary( dllFolder + r'\NKTPDLL\x86\NKTPDLL.dll' )
else:
        print('Loading x64 DLL from:', dllFolder + r'\NKTPDLL\x64\NKTPDLL.dll')
        NKTPDLL = ctypes.cdll.LoadLibrary( dllFolder + r'\NKTPDLL\x64\NKTPDLL.dll')

def PortResultTypes(result):
        return {
                0: '0:OPSuccess',
                1: '1:OPFailed',
                2: '2:OPPortNotFound',
                3: '3:OPNoDevices',
                4: '4:OPApplicationBusy',
                }.get(result, 'Unknown result')

def P2PPortResultTypes(result):
        return {
                0: '0:P2PSuccess',
                1: '1:P2PInvalidPortname',
                2: '2:P2PInvalidLocalIP',
                3: '3:P2PInvalidRemoteIP',
                4: '4:P2PPortnameNotFound',
                5: '5:P2PPortnameExists',
                6: '6:P2PApplicationBusy',
                }.get(result, 'Unknown result')

def DeviceResultTypes(result):
        return {
                0: '0:DevResultSuccess',
                1: '1:DevResultWaitTimeout',
                2: '2:DevResultFailed',
                3: '3:DevResultDeviceNotFound',
                4: '4:DevResultPortNotFound',
                5: '5:DevResultPortOpenError',
                6: '6:DevResultApplicationBusy',
                }.get(result, 'Unknown result')

def DeviceModeTypes(mode):
        return {
                0: '0:DevModeDisabled',
                1: '1:DevModeAnalyzeInit',
                2: '2:DevModeAnalyze',
                3: '3:DevModeNormal',
                4: '4:DevModeLogDownload',
                5: '5:DevModeError',
                6: '6:DevModeTimeout',
                7: '7:DevModeUpload',
                }.get(mode, 'Unknown mode' + str(mode))

def RegisterResultTypes(result):
        return {
                0: '0:RegResultSuccess',
                1: '1:RegResultReadError',
                2: '2:RegResultFailed',
                3: '3:RegResultBusy',
                4: '4:RegResultNacked',
                5: '5:RegResultCRCErr',
                6: '6:RegResultTimeout',
                7: '7:RegResultComError',
                8: '8:RegResultTypeError',
                9: '9:RegResultIndexError',
                10: '10:RegResultPortClosed',
                11: '11:RegResultRegisterNotFound',
                12: '12:RegResultDeviceNotFound',
                13: '13:RegResultPortNotFound',
                14: '14:RegResultPortOpenError',
                15: '15:RegResultApplicationBusy',
                }.get(result, 'Unknown result')

def RegisterDataTypes(datatype):
        return {
                0: '0:RegData_Unknown',
                1: '1:RegData_Array',
                2: '2:RegData_U8',
                3: '3:RegData_S8',
                4: '4:RegData_U16',
                5: '5:RegData_S16',
                6: '6:RegData_U32',
                7: '7:RegData_S32',
                8: '8:RegData_F32',
                9: '9:RegData_U64',
                10: '10:RegData_S64',
                11: '11:RegData_F64',
                12: '12:RegData_Ascii',
                13: '13:RegData_Paramset',
                14: '14:RegData_B8',
                15: '15:RegData_H8',
                16: '16:RegData_B16',
                17: '17:RegData_H16',
                18: '18:RegData_B32',
                19: '19:RegData_H32',
                20: '20:RegData_B64',
                21: '21:RegData_H64',
                22: '22:RegData_DateTime',
                }.get(datatype, 'Unknown data type')

def RegisterPriorityTypes(priority):
        return {
                0: '0:RegPriority_Low',
                1: '1:RegPriority_High',
                }.get(priority, 'Unknown priority')

def PortStatusTypes(status):
        return {
                0: '0:PortStatusUnknown',
                1: '1:PortOpening',
                2: '2:PortOpened',
                3: '3:PortOpenFail',
                4: '4:PortScanStarted',
                5: '5:PortScanProgress',
                6: '6:PortScanDeviceFound',
                7: '7:PortScanEnded',
                8: '8:PortClosing',
                9: '9:PortClosed',
                10: '10:PortReady',
                }.get(status, 'Unknown status')

def DeviceStatusTypes(status):
        return {
                0: '0:DeviceModeChanged',
                1: '1:DeviceLiveChanged',
                2: '2:DeviceTypeChanged',
                3: '3:DevicePartNumberChanged',
                4: '4:DevicePCBVersionChanged',
                5: '5:DeviceStatusBitsChanged',
                6: '6:DeviceErrorCodeChanged',
                7: '7:DeviceBlVerChanged',
                8: '8:DeviceFwVerChanged',
                9: '9:DeviceModuleSerialChanged',
                10: '10:DevicePCBSerialChanged',
                11: '11:DeviceSysTypeChanged',
                }.get(status, 'Unknown status')

def RegisterStatusTypes(status):
        return {
                0: '0:RegSuccess',
                1: '1:RegBusy',
                2: '2:RegNacked',
                3: '3:RegCRCErr',
                4: '4:RegTimeout',
                5: '5:RegComError',
                }.get(status, 'Unknown status')

class tDateTimeStruct(ctypes.Structure):
        _fields_ = [('Sec', c_ubyte),           #!< Seconds
                    ('Min', c_ubyte),           #!< Minutes
                    ('Hour', c_ubyte),          #!< Hours
                    ('Day', c_ubyte),           #!< Days
                    ('Month', c_ubyte),         #!< Months
                    ('Year', c_ubyte)]          #!< Years

def ParamSetUnitTypes(unit):
        return {
                0: '0:Unit None',
                1: '1:Unit mV',
                2: '2:Unit V',
                3: '3:Unit uA',
                4: '4:Unit mA',
                5: '5:Unit A',
                6: '6:Unit uW',
                7: '7:Unit cmW',
                8: '8:Unit dmW',
                9: '9:Unit mW',
                10: '10:Unit W',
                11: '11:Unit mC',
                12: '12:Unit cC',
                13: '13:Unit dC',
                14: '14:Unit pm',
                15: '15:Unit dnm',
                16: '16:Unit nm',
                17: '17:Unit PerCent',
                18: '18:Unit PerMille',
                19: '19:Unit cmA',
                20: '20:Unit dmA',
                21: '21:Unit RPM',
                22: '22:Unit dBm',
                23: '23:Unit cBm',
                24: '24:Unit mBm',
                25: '25:Unit dB',
                26: '26:Unit cB',
                27: '27:Unit mB',
                28: '28:Unit dpm',
                29: '29:Unit cV',
                30: '30:Unit dV',
                31: '31:Unit lm',
                32: '32:Unit dlm',
                33: '33:Unit clm',
                34: '34:Unit mlm',
                }.get(unit, 'Unknown unit')

# tParamSetStruct, The ParameterSet struct
# * \note How calculation on parametersets is done internally by modules:\n
# * DAC_value = (value * (X/Y)) + Offset; Where value is either StartVal or FactoryVal\n
# * value = (ADC_value * (X/Y)) + Offset; Where value often is available via another measurement register\n
class tParamSetStruct(ctypes.Structure):
        _fields_ = [('Unit', c_ubyte),                  #!< Unit type as defined in ::ParamSetUnitTypes
                    ('ErrorHandler', c_ubyte),          #!< Warning/Errorhandler not used.
                    ('StartVal', c_ushort),             #!< Setpoint for Settings parameterset, unused in Measurement parametersets.
                    ('FactoryVal', c_ushort),           #!< Factory Setpoint for Settings parameterset, unused in Measurement parametersets.
                    ('ULimit', c_ushort),               #!< Upper limit.
                    ('LLimit', c_ushort),               #!< Lower limit.
                    ('Numerator', c_short),             #!< Numerator(X) for calculation.
                    ('Denominator', c_short),           #!< Denominator(Y) for calculation.
                    ('Offset', c_short)]                #!< Offset for calculation


#*******************************************************************************************************
# Port functions
#*******************************************************************************************************
# Port functions

# \brief Returns a comma separated string with all existing ports.
# \param portnames Pointer to a preallocated string area where the function will store the comma separated string.
# \param maxLen Size of preallocated string area. The returned string may be truncated to fit into the allocated area.
#
# extern "C" NKTPDLL_EXPORT void getAllPorts(char *portnames, unsigned short *maxLen);
# typedef void (__cdecl *GetAllPortsFuncPtr)(char *portnames, unsigned short *maxLen);
_getAllPorts = CFUNCTYPE(None, POINTER(c_char), POINTER(c_ushort))(('getAllPorts', NKTPDLL))
def getAllPorts():
	maxLen = c_ushort(255)
	portnames = create_string_buffer(maxLen.value)
	_getAllPorts(portnames, byref(maxLen))
	return portnames.value.decode('ascii')

# \brief Returns a comma separated string with all allready opened ports.
# \param portnames Pointer to a preallocated string area where the function will store the comma separated string.
# \param maxLen Size of preallocated string area. The returned string may be truncated to fit into the allocated area.
#
# extern "C" NKTPDLL_EXPORT void getOpenPorts(char *portnames, unsigned short *maxLen);
# typedef void (__cdecl *GetOpenPortsFuncPtr)(char *portnames, unsigned short *maxLen);
_getOpenPorts = CFUNCTYPE(None, POINTER(c_char), POINTER(c_ushort))(('getOpenPorts', NKTPDLL))
def getOpenPorts():
	maxLen = c_ushort(255)
	portnames = create_string_buffer(maxLen.value)
	_getOpenPorts(portnames, byref(maxLen))
	return portnames.value.decode('ascii')

# Named tuple for PointToPoint ports	
pointToPointPortData = namedtuple('pointToPointPortData', 'hostAddress, hostPort, clientAddress, clientPort, protocol, msTimeout')	
	
# \brief Creates or Modifies a point to point port.
# \param portname Zero terminated string giving the portname. ex. "AcoustikPort1"
# \param hostAddress Zero terminated string giving the local ip address. ex. "192.168.1.67"
# \param hostPort The local port number.
# \param clientAddress Zero terminated string giving the remote ip address. ex. "192.168.1.100"
# \param clientPort The remote port number.
# \param protocol \arg 0 Specifies TCP protocol.
#                 \arg 1 Specifies UDP protocol.
# \param msTimeout Telegram timeout value in milliseconds, typically set to 100ms.
# \return ::P2PPortResultTypes
#
# extern "C" NKTPDLL_EXPORT P2PPortResultTypes pointToPointPortAdd(const char *portname, const char *hostAddress, const unsigned short hostPort, const char *clientAddress, const unsigned short clientPort, const unsigned char protocol, const unsigned char msTimeout);
# typedef P2PPortResultTypes (__cdecl *PointToPointPortAddFuncPtr)(const char *portname, const char *hostAddress, const unsigned short hostPort, const char *clientAddress, const unsigned short clientPort, const unsigned char protocol, const unsigned char msTimeout);
_pointToPointPortAdd = CFUNCTYPE(c_ubyte, c_char_p, c_char_p, c_ushort, c_char_p, c_ushort, c_ubyte, c_ubyte)(('pointToPointPortAdd', NKTPDLL))
def pointToPointPortAdd(portname, portdata):
	return _pointToPointPortAdd(portname.encode('ascii'), portdata.hostAddress.encode('ascii'), portdata.hostPort, portdata.clientAddress.encode('ascii'), portdata.clientPort, portdata.protocol, portdata.msTimeout)
	
# \brief Retrieve an already created point to point port setting.
# \param portname Zero terminated string giving the portname (case sensitive). ex. "AcoustikPort1"
# \param hostAddress Pointer to a preallocated string area where the function will store the zero terminated string, describing the local ip address.
# \param hostMaxLen Pointer to an unsigned char giving the size of the preallocated hostAddress area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \param hostPort Pointer to a preallocated short where the function will store the local port number.
# \param clientAddress Pointer to a preallocated string area where the function will store the zero terminated string, describing the remote ip address.
# \param clientMaxLen Pointer to an unsigned char giving the size of the preallocated clientAddress area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \param clientPort Pointer to a preallocated short where the function will store the client port number.
# \param protocol Pointer to a preallocated char where the function will store the protocol.
#                  \arg 0 Specifies TCP protocol.
#                  \arg 1 Specifies UDP protocol.
# \param msTimeout Pointer to a preallocated char where the function will store the timeout value.
# \return ::P2PPortResultTypes
#
# extern "C" NKTPDLL_EXPORT P2PPortResultTypes pointToPointPortGet(const char *portname, char *hostAddress, unsigned char *hostMaxLen, unsigned short *hostPort, char *clientAddress, unsigned char *clientMaxLen, unsigned short *clientPort, unsigned char *protocol, unsigned char *msTimeout);
# typedef P2PPortResultTypes (__cdecl *PointToPointPortGetFuncPtr)(const char *portname, char *hostAddress, unsigned char *hostMaxLen, unsigned short *hostPort, char *clientAddress, unsigned char *clientMaxLen, unsigned short *clientPort, unsigned char *protocol, unsigned char *msTimeout);
_pointToPointPortGet = CFUNCTYPE(c_ubyte, c_char_p, POINTER(c_char), POINTER(c_ubyte), POINTER(c_ushort), POINTER(c_char), POINTER(c_ubyte), POINTER(c_ushort), POINTER(c_ubyte), POINTER(c_ubyte))(('pointToPointPortGet', NKTPDLL))
def pointToPointPortGet(portname): #, hostAddress, hostPort, clientAddress, clientPort, protocol, msTimeout):
	_hostMaxLen = c_ubyte(255)
	_hostAddress = create_string_buffer(_hostMaxLen.value)
	_hostPort = c_ushort(0)
	_clientMaxLen = c_ubyte(255)
	_clientAddress = create_string_buffer(_clientMaxLen.value)
	_clientPort = c_ushort(0)
	_protocol = c_ubyte(0)
	_msTimeout = c_ubyte(0)
	result = _pointToPointPortGet(portname.encode('ascii'), _hostAddress, _hostMaxLen, _hostPort, _clientAddress, _clientMaxLen, _clientPort, _protocol, _msTimeout)
	return result, pointToPointPortData(_hostAddress.value.decode('ascii'),_hostPort.value,_clientAddress.value.decode('ascii'),_clientPort.value,_protocol.value,_msTimeout.value)

# \brief Delete an already created point to point port.
# \param portname Zero terminated string giving the portname (case sensitive). ex. "AcoustikPort1"
# \return ::P2PPortResultTypes
#
# extern "C" NKTPDLL_EXPORT P2PPortResultTypes pointToPointPortDel(const char *portname);
# typedef P2PPortResultTypes (__cdecl *PointToPointPortDelFuncPtr)(const char *portname);
_pointToPointPortDel = CFUNCTYPE(c_ubyte, c_char_p)(('pointToPointPortDel', NKTPDLL))
def pointToPointPortDel(portname):
	return _pointToPointPortDel(portname.encode('ascii'))
	
# \brief Opens the provided portname(s), or all available ports if an empty string provided. Repeatedly calls is allowed to reopen and/or rescan for devices.\n
# \param portnames Zero terminated comma separated string giving the portnames to open (case sensitive). An empty string opens all available ports.
# \param autoMode \arg 0 the openPorts function only opens the port. Busscanning and device creation is NOT automatically handled.
#                 \arg 1 the openPorts function will automatically start the busscanning and create the found devices in the internal devicelist. The port is automatically closed if no devices found.
# \param liveMode \arg 0 the openPorts function disables the continuously monitoring of the registers. No callback possible on register changes. Use ::registerRead, ::registerWrite & ::registerWriteRead functions.
#                 \arg 1 the openPorts function will keep all the found or created devices in live mode, which means the Interbus kernel keeps monitoring all the found devices and their registers.
#                  Please note that this will keep the modules watchdog alive as long as the port is open.
# \return ::PortResultTypes
# \note The function may timeout after 2 seconds waiting for port ready status and return ::OPFailed.\n
#       In case autoMode is specified this timeout is extended to 20 seconds to allow for busscanning to complete.
#
# extern "C" NKTPDLL_EXPORT PortResultTypes openPorts(const char *portnames, const char autoMode, const char liveMode);
# typedef PortResultTypes (__cdecl *OpenPortsFuncPtr)(const char *portnames, const char autoMode, const char liveMode);
_openPorts = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte)(('openPorts', NKTPDLL))
def openPorts(portnames, autoMode, liveMode):
	return _openPorts(portnames.encode('ascii'), autoMode, liveMode)

# \brief Closes the provided portname(s), or all opened ports if an empty string provided.
# \param portnames Zero terminated comma separated string giving the portnames to close (case sensitive). An empty string closes all open ports.
# \return ::PortResultTypes
# \note The function may timeout after 2 seconds waiting for port close to complete and return ::OPFailed.
#
# extern "C" NKTPDLL_EXPORT PortResultTypes closePorts(const char *portnames);
# typedef PortResultTypes (__cdecl *ClosePortsFuncPtr)(const char *portnames);
_closePorts = CFUNCTYPE(c_ubyte, c_char_p)(('closePorts', NKTPDLL))
def closePorts(portnames):
	return _closePorts(portnames.encode('ascii'))

# \brief Sets legacy busscanning on or off.
# \param legacyScanning \arg 0 the busscanning is set to normal mode and allows for rolling masterId. In this mode the masterId is changed for each message to allow for out of sync. detection.
#                       \arg 1 the busscanning is set to legacy mode and fixes the masterId at address 66(0x42). Some older modules does not accept masterIds other than 66(ox42).
# extern "C" NKTPDLL_EXPORT void setLegacyBusScanning(const char legacyScanning);
# typedef void (__cdecl *SetLegacyBusScanningFuncPtr)(const char legacyScanning);
_setLegacyBusScanning = CFUNCTYPE(None, c_ubyte)(('setLegacyBusScanning', NKTPDLL))
def setLegacyBusScanning(legacyScanning):
	return _setLegacyBusScanning(legacyScanning)

# \brief Gets legacy busscanning status.
# \return An unsigned char, with legacyScanning status. 0 the busscanning is currently in normal mode. 1 the busscanning is currently in legacy mode.
# extern "C" NKTPDLL_EXPORT unsigned char getLegacyBusScanning();
# typedef unsigned char (__cdecl *GetLegacyBusScanningFuncPtr)();
_getLegacyBusScanning = CFUNCTYPE(c_ubyte)(('getLegacyBusScanning', NKTPDLL))
def getLegacyBusScanning():
        return _getLegacyBusScanning()
	
# \brief Retrieve ::PortStatusTypes for a given port.
# \param portname Zero terminated string giving the portname (case sensitive). ex. "COM1"
# \param portStatus Pointer to a ::PortStatusTypes where the function will store the port status.
# \return ::PortResultTypes
#
# extern "C" NKTPDLL_EXPORT PortResultTypes getPortStatus(const char *portname, PortStatusTypes *portStatus);
# typedef PortResultTypes (__cdecl *getPortStatusFuncPtr)(const char *portname, PortStatusTypes *portStatus);
_getPortStatus = CFUNCTYPE(c_ubyte, c_char_p, POINTER(c_ubyte))(('getPortStatus', NKTPDLL))
def getPortStatus(portname):
        portStatus = c_ubyte(0)
        result = _getPortStatus(portname.encode('ascii'), portStatus)
        return result, portStatus.value

# \brief Retrieve error message for a given port. An empty string indicates no error.
# \param portname Zero terminated string giving the portname (case sensitive). ex. "COM1"
# \param errorMessage Pointer to a preallocated string area where the function will store the zero terminated error string.
# \param maxLen Pointer to an unsigned short giving the size of the preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
#
# extern "C" NKTPDLL_EXPORT PortResultTypes getPortErrorMsg(const char *portname, char *errorMessage, unsigned short *maxLen);
# typedef PortResultTypes (__cdecl *getPortErrorMsgFuncPtr)(const char *portname, char *errorMessage, unsigned short *maxLen);
_getPortErrorMsg = CFUNCTYPE(c_ubyte, c_char_p, POINTER(c_char), POINTER(c_ushort))(('getPortErrorMsg', NKTPDLL))
def getPortErrorMsg(portname):
	_maxLen = c_ushort(1000)
	_errMsg = create_string_buffer(_maxLen.value)
	result = _getPortErrorMsg(portname.encode('ascii'), _errMsg, _maxLen)
	return result, _errMsg.value.decode('ascii')

#*******************************************************************************************************
# Dedicated - Register read functions
#*******************************************************************************************************
# Dedicated - Register read functions.
# It is not necessary to open the port, create the device or register before using those functions, since they will do a dedicated action.
# Even though an already opened port would be preffered in time critical situations where a lot of reads is required.

# \brief Reads a register value and returns the result in readData area.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param readData Pointer to a preallocated data area where the function will store the register value.
# \param readSize Size of preallocated data area, modified by the function to reflect the actual length of the returned register value. The returned register value may be truncated to fit into the allocated area.
# \param index Data index. Typically -1, but could be used to extract data from a specific position in the register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \sa ::registerReadU8, ::registerReadS8 etc.
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerRead(const char *portname, const unsigned char devId, const unsigned char regId, void *readData, unsigned char *readSize, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, void *readData, unsigned char *readSize, const short index);
_registerRead = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_char), POINTER(c_ubyte), c_short)(('registerRead', NKTPDLL))
def registerRead(portname, devId, regId, index):
	_readSize = c_ubyte(255)
	_readData = create_string_buffer(_readSize.value)
	result = _registerRead(portname.encode('ascii'), devId, regId, _readData, _readSize, index)
	if result != 0: _readSize = c_ubyte(0)
	return result, _readData.raw[:_readSize.value]

# \brief Reads an unsigned char (8bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to an unsigned char where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadU8(const char *portname, const unsigned char devId, const unsigned char regId, unsigned char *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadU8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, unsigned char *value, const short index);
_registerReadU8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_ubyte), c_short)(('registerReadU8', NKTPDLL))
def registerReadU8(portname, devId, regId, index):
	_readValue = c_ubyte(0)
	result = _registerReadU8(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a signed char (8bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a signed char where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadS8(const char *portname, const unsigned char devId, const unsigned char regId, signed char *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadS8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, signed char *value, const short index);
_registerReadS8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_byte), c_short)(('registerReadS8', NKTPDLL))
def registerReadS8(portname, devId, regId, index):
	_readValue = c_byte(0)
	result = _registerReadS8(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads an unsigned short (16bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to an unsigned short where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadU16(const char *portname, const unsigned char devId, const unsigned char regId, unsigned short *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadU16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, unsigned short *value, const short index);
_registerReadU16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_ushort), c_short)(('registerReadU16', NKTPDLL))
def registerReadU16(portname, devId, regId, index):
	_readValue = c_ushort(0)
	result = _registerReadU16(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a signed short (16bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a signed short where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadS16(const char *portname, const unsigned char devId, const unsigned char regId, signed short *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadS16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, signed short *value, const short index);
_registerReadS16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_short), c_short)(('registerReadS16', NKTPDLL))
def registerReadS16(portname, devId, regId, index):
	_readValue = c_short(0)
	result = _registerReadS16(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads an unsigned long (32bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to an unsigned long where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadU32(const char *portname, const unsigned char devId, const unsigned char regId, unsigned long *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadU32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, unsigned long *value, const short index);
_registerReadU32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_ulong), c_short)(('registerReadU32', NKTPDLL))
def registerReadU32(portname, devId, regId, index):
	_readValue = c_ulong(0)
	result = _registerReadU32(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a signed long (32bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a signed long where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadS32(const char *portname, const unsigned char devId, const unsigned char regId, signed long *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadS32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, signed long *value, const short index);
_registerReadS32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_long), c_short)(('registerReadS32', NKTPDLL))
def registerReadS32(portname, devId, regId, index):
	_readValue = c_long(0)
	result = _registerReadS32(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value
    
# \brief Reads an unsigned long long (64bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to an unsigned long long where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadU64(const char *portname, const unsigned char devId, const unsigned char regId, unsigned long long *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadU64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, unsigned long long *value, const short index);
_registerReadU64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_ulonglong), c_short)(('registerReadU64', NKTPDLL))
def registerReadU64(portname, devId, regId, index):
	_readValue = c_ulonglong(0)
	result = _registerReadU64(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a signed long long (64bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a signed long long where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadS64(const char *portname, const unsigned char devId, const unsigned char regId, signed long long *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadS64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, signed long long *value, const short index);
_registerReadS64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_longlong), c_short)(('registerReadS64', NKTPDLL))
def registerReadS64(portname, devId, regId, index):
	_readValue = c_longlong(0)
	result = _registerReadS64(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a float (32bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a float where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadF32(const char *portname, const unsigned char devId, const unsigned char regId, float *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadF32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, float *value, const short index);
_registerReadF32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_float), c_short)(('registerReadF32', NKTPDLL))
def registerReadF32(portname, devId, regId, index):
	_readValue = c_float(0)
	result = _registerReadF32(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a double (64bit) register value and returns the result in value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value Pointer to a double where the function will store the register value.
# \param index Value index. Typically -1, but could be used to extract a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadF64(const char *portname, const unsigned char devId, const unsigned char regId, double *value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadF64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, double *value, const short index);
_registerReadF64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_double), c_short)(('registerReadF64', NKTPDLL))
def registerReadF64(portname, devId, regId, index):
	_readValue = c_double(0)
	result = _registerReadF64(portname.encode('ascii'), devId, regId, _readValue, index)
	return result, _readValue.value

# \brief Reads a Ascii string register value and returns the result in readStr area.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param readStr Pointer to a preallocated string area where the function will store the register value.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \param index Value index. Typically -1, but could be used to extract a string in a mixed type register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerReadAscii(const char *portname, const unsigned char devId, const unsigned char regId, char *readStr, unsigned char *maxLen, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterReadAsciiFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, char *readStr, unsigned char *maxLen, const short index);
_registerReadAscii = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_char), POINTER(c_ubyte), c_short)(('registerReadAscii', NKTPDLL))
def registerReadAscii(portname, devId, regId, index):
	_readSize = c_ubyte(255)
	_readData = create_string_buffer(_readSize.value)
	result = _registerReadAscii(portname.encode('ascii'), devId, regId, _readData, _readSize, index)
	return result, _readData.value


#*******************************************************************************************************
#* Dedicated - Register write functions
#*******************************************************************************************************/
# Dedicated - Register write functions.
# It is not necessary to open the port, create the device or register before using those functions, since they will do a dedicated action.
# Even though an already opened port would be preffered in time critical situations where a lot of reads or writes is required.

# \brief Writes a register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeData Pointer to a data area from where the write value will be extracted.
# \param writeSize Size of data area, ex. number of bytes to write. Write size is limited to max 240 bytes
# \param index Data index. Typically -1, but could be used to write data at a specific position in the register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \sa ::registerWriteU8, ::registerWriteS8 etc.
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWrite(const char *portname, const unsigned char devId, const unsigned char regId, const void *writeData, const unsigned char writeSize, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterWriteFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const void *writeData, const unsigned char writeSize, const short index);
_registerWrite = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_char), c_ubyte, c_short)(('registerWrite', NKTPDLL))
def registerWrite(portname, devId, regId, writeData, writeSize, index):
        return _registerWrite(portname.encode('ascii'), devId, regId, writeData, writeSize, index)

# \brief Writes an unsigned char (8bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
# extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteU8(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned char value, const short index);
# typedef RegisterResultTypes (__cdecl *RegisterWriteU8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned char value, const short index);
_registerWriteU8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ubyte, c_short)(('registerWriteU8', NKTPDLL))
def registerWriteU8(portname, devId, regId, value, index):
	return _registerWriteU8(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a signed char (8bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
#
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteS8(const char *portname, const unsigned char devId, const unsigned char regId, const signed char value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteS8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed char value, const short index);
_registerWriteS8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_byte, c_short)(('registerWriteS8', NKTPDLL))
def registerWriteS8(portname, devId, regId, value, index):
	return _registerWriteS8(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes an unsigned short (16bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteU16(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned short value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteU16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned short value, const short index);
_registerWriteU16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ushort, c_short)(('registerWriteU16', NKTPDLL))
def registerWriteU16(portname, devId, regId, value, index):
	return _registerWriteU16(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a signed short (16bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteS16(const char *portname, const unsigned char devId, const unsigned char regId, const signed short value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteS16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed short value, const short index);
_registerWriteS16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_short, c_short)(('registerWriteS16', NKTPDLL))
def registerWriteS16(portname, devId, regId, value, index):
	return _registerWriteS16(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes an unsigned long (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteU32(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteU32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long value, const short index);
_registerWriteU32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ulong, c_short)(('registerWriteU32', NKTPDLL))
def registerWriteU32(portname, devId, regId, value, index):
	return _registerWriteU32(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a signed long (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteS32(const char *portname, const unsigned char devId, const unsigned char regId, const signed long value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteS32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed long value, const short index);
_registerWriteS32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_long, c_short)(('registerWriteS32', NKTPDLL))
def registerWriteS32(portname, devId, regId, value, index):
	return _registerWriteS32(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes an unsigned long long (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteU64(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long long value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteU64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long long value, const short index);
_registerWriteU64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ulonglong, c_short)(('registerWriteU64', NKTPDLL))
def registerWriteU64(portname, devId, regId, value, index):
	return _registerWriteU64(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a signed long long (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteS64(const char *portname, const unsigned char devId, const unsigned char regId, const signed long long value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteS64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed long long value, const short index);
_registerWriteS64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_longlong, c_short)(('registerWriteS64', NKTPDLL))
def registerWriteS64(portname, devId, regId, value, index):
	return _registerWriteS64(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a float (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteF32(const char *portname, const unsigned char devId, const unsigned char regId, const float value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteF32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const float value, const short index);
_registerWriteF32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_float, c_short)(('registerWriteF32', NKTPDLL))
def registerWriteF32(portname, devId, regId, value, index):
	return _registerWriteF32(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a double (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param value The register value to write.
# \param index Value index. Typically -1, but could be used to write a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteF64(const char *portname, const unsigned char devId, const unsigned char regId, const double value, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteF64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const double value, const short index);
_registerWriteF64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_double, c_short)(('registerWriteF64', NKTPDLL))
def registerWriteF64(portname, devId, regId, value, index):
	return _registerWriteF64(portname.encode('ascii'), devId, regId, value, index)

# \brief Writes a string register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeStr The zero terminated string to write. WriteStr will be limited to 239 characters and the terminating zero, totally 240 bytes.
# \param writeEOL \arg 0 Do NOT append End Of Line character (a null character) to the string.
#                 \arg 1 Append End Of Line character to the string.
# \param index Value index. Typically -1, but could be used to write a value in a mixed type register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteAscii(const char *portname, const unsigned char devId, const unsigned char regId, const char* writeStr, const char writeEOL, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteAsciiFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const char* writeStr, const char writeEOL, const short index);
_registerWriteAscii = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_char_p, c_ubyte, c_short)(('registerWriteAscii', NKTPDLL))
def registerWriteAscii(portname, devId, regId, strValue, wrEOL, index):
        _asciiValue = create_string_buffer(strValue.encode('ascii'))
        return _registerWriteAscii(portname.encode('ascii'), devId, regId, _asciiValue, wrEOL, index)


#*******************************************************************************************************
#* Dedicated - Register write/read functions (A write immediately followed by a read)
#*******************************************************************************************************/
# Dedicated - Register write/read functions (A write immediately followed by a read)
# It is not necessary to open the port, create the device or register before using those functions, since they will do a dedicated action.
# Even though an already opened port would be preffered in time critical situations where a lot of reads or writes is required.

# \brief Writes and Reads a register value before returning.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeData Pointer to a data area from where the write value will be extracted.
# \param writeSize Size of write data area, ex. number of bytes to write.
# \param readData Pointer to a preallocated data area where the function will store the register read value.
# \param readSize Size of preallocated read data area, modified by the function to reflect the actual length of the read register value. The read register value may be truncated to fit into the allocated area.
# \param index Data index. Typically -1, but could be used to write/read data at/from a specific position in the register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \sa ::registerWriteReadU8, ::registerWriteReadS8 etc.
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteRead(const char *portname, const unsigned char devId, const unsigned char regId, const void *writeData, const unsigned char writeSize, void *readData, unsigned char *readSize, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const void *writeData, const unsigned char writeSize, void *readData, unsigned char *readSize, const short index);
_registerWriteRead = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_char), c_ubyte, POINTER(c_char), POINTER(c_ubyte), c_short)(('registerWriteRead', NKTPDLL))
def registerWriteRead(portname, devId, regId, writeData, writeSize, index):
        _readSize = c_ubyte(255)
        _readData = create_string_buffer(_readSize.value)
        result = _registerWriteRead(portname.encode('ascii'), devId, regId, writeData, writeSize, _readData, _readSize, index)
        return result, _readData.raw[:_readSize.value]

# \brief Writes and Reads an unsigned char (8bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to an unsigned char where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadU8(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned char writeValue, unsigned char *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadU8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned char writeValue, unsigned char *readValue, const short index);
_registerWriteReadU8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ubyte, POINTER(c_ubyte), c_short)(('registerWriteReadU8', NKTPDLL))
def registerWriteReadU8(portname, devId, regId, writeValue, index):
        _readValue = c_ubyte(0)
        result = _registerWriteReadU8(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a signed char (8bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a signed char where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadS8(const char *portname, const unsigned char devId, const unsigned char regId, const signed char writeValue, signed char *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadS8FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed char writeValue, signed char *readValue, const short index);
_registerWriteReadS8 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_byte, POINTER(c_byte), c_short)(('registerWriteReadS8', NKTPDLL))
def registerWriteReadS8(portname, devId, regId, writeValue, index):
        _readValue = c_byte(0)
        result = _registerWriteReadS8(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads an unsigned short (16bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to an unsigned short where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadU16(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned short writeValue, unsigned short *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadU16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned short writeValue, unsigned short *readValue, const short index);
_registerWriteReadU16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ushort, POINTER(c_ushort), c_short)(('registerWriteReadU16', NKTPDLL))
def registerWriteReadU16(portname, devId, regId, writeValue, index):
        _readValue = c_ushort(0)
        result = _registerWriteReadU16(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a signed short (16bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a signed short where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadS16(const char *portname, const unsigned char devId, const unsigned char regId, const signed short writeValue, signed short *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadS16FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed short writeValue, signed short *readValue, const short index);
_registerWriteReadS16 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_short, POINTER(c_short), c_short)(('registerWriteReadS16', NKTPDLL))
def registerWriteReadS16(portname, devId, regId, writeValue, index):
        _readValue = c_short(0)
        result = _registerWriteReadS16(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads an unsigned long (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to an unsigned long where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadU32(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long writeValue, unsigned long *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadU32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long writeValue, unsigned long *readValue, const short index);
_registerWriteReadU32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ulong, POINTER(c_ulong), c_short)(('registerWriteReadU32', NKTPDLL))
def registerWriteReadU32(portname, devId, regId, writeValue, index):
        _readValue = c_ulong(0)
        result = _registerWriteReadU32(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a signed long (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a signed long where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadS32(const char *portname, const unsigned char devId, const unsigned char regId, const signed long writeValue, signed long *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadS32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed long writeValue, signed long *readValue, const short index);
_registerWriteReadS32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_long, POINTER(c_long), c_short)(('registerWriteReadS32', NKTPDLL))
def registerWriteReadS32(portname, devId, regId, writeValue, index):
        _readValue = c_long(0)
        result = _registerWriteReadS32(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads an unsigned long long (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to an unsigned long long where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadU64(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long long writeValue, unsigned long long *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadU64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const unsigned long long writeValue, unsigned long long *readValue, const short index);
_registerWriteReadU64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ulonglong, POINTER(c_ulonglong), c_short)(('registerWriteReadU64', NKTPDLL))
def registerWriteReadU64(portname, devId, regId, writeValue, index):
        _readValue = c_ulonglong(0)
        result = _registerWriteReadU64(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a signed long long (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a signed long long where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadS64(const char *portname, const unsigned char devId, const unsigned char regId, const signed long long writeValue, signed long long *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadS64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const signed long long writeValue, signed long long *readValue, const short index);
_registerWriteReadS64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_longlong, POINTER(c_longlong), c_short)(('registerWriteReadS64', NKTPDLL))
def registerWriteReadS64(portname, devId, regId, writeValue, index):
        _readValue = c_longlong(0)
        result = _registerWriteReadS64(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a float (32bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a float where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadF32(const char *portname, const unsigned char devId, const unsigned char regId, const float writeValue, float *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadF32FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const float writeValue, float *readValue, const short index);
_registerWriteReadF32 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_float, POINTER(c_float), c_short)(('registerWriteReadF32', NKTPDLL))
def registerWriteReadF32(portname, devId, regId, writeValue, index):
        _readValue = c_float(0)
        result = _registerWriteReadF32(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a double (64bit) register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeValue The register value to write.
# \param readValue Pointer to a double where the function will store the register read value.
# \param index Value index. Typically -1, but could be used to write and read a value in a multi value register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadF64(const char *portname, const unsigned char devId, const unsigned char regId, const double writeValue, double *readValue, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadF64FuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const double writeValue, double *readValue, const short index);
_registerWriteReadF64 = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_double, POINTER(c_double), c_short)(('registerWriteReadF64', NKTPDLL))
def registerWriteReadF64(portname, devId, regId, writeValue, index):
        _readValue = c_double(0)
        result = _registerWriteReadF64(portname.encode('ascii'), devId, regId, writeValue, _readValue, index)
        return result, _readValue.value

# \brief Writes and Reads a string register value.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param writeStr The zero terminated string to write. WriteStr will be limited to 239 characters and the terminating zero, totally 240 bytes.
# \param writeEOL \arg 0 Do NOT append End Of Line character (a null character) to the string.
#                 \arg 1 Append End Of Line character to the string.
# \param readStr Pointer to a preallocated string area where the function will store the register read value.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \param index Value index. Typically -1, but could be used to write and read a string in a mixed type register. Index is byte counted.
# \return A status result value ::RegisterResultTypes
# \note It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated write followed by a dedicated read.
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerWriteReadAscii(const char *portname, const unsigned char devId, const unsigned char regId, const char* writeStr, const char writeEOL, char *readStr, unsigned char *maxLen, const short index);
#typedef RegisterResultTypes (__cdecl *RegisterWriteReadAsciiFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const char* writeStr, const char writeEOL, char *readStr, unsigned char *maxLen, const short index);
_registerWriteReadAscii = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte), c_short)(('registerWriteReadAscii', NKTPDLL))
def registerWriteReadAscii(portname, devId, regId, strValue, wrEOL, index):
        _asciiValue = create_string_buffer(strValue.encode('ascii'))
        _readSize = c_ubyte(255)
        _readData = create_string_buffer(_readSize.value)
        result = _registerWriteReadAscii(portname.encode('ascii'), devId, regId, _asciiValue, wrEOL, _readData, _readSize, index)
        return result, _readData.value

#*******************************************************************************************************
#* Dedicated - Device functions
#*******************************************************************************************************/
# Dedicated - Device functions could be used directly.\n
# It is not necessary to open the port, create the device or register before using those functions, since they will do a dedicated action.
# Even though an already opened port would be preffered in time critical situations where a lot of reads is required.

# \brief Returns the module type for a specific device id (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId Given device id to retrieve device type for (module type).
# \param devType Pointer to an unsigned char where the function stores the device type.
# \return A status result value ::DeviceResultTypes
# \note Register address 0x61\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetType(const char *portname, const unsigned char devId, unsigned char *devType);
#typedef DeviceResultTypes (__cdecl *DeviceGetTypeFuncPtr)(const char *portname, const unsigned char devId, unsigned char *devType);
_deviceGetType = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ubyte))(('deviceGetType', NKTPDLL))
def deviceGetType(portname, devId):
	_readValue = c_ubyte(0)
	result = _deviceGetType(portname.encode('ascii'), devId, _readValue)
	return result, _readValue.value

# \brief Returns the partnumber for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param partnumber Pointer to a preallocated string area where the function will store the partnumber.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x8E <b>Not all modules have a partnumber register.</b>\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetPartNumberStr(const char *portname, const unsigned char devId, char *partnumber, unsigned char *maxLen);
#typedef DeviceResultTypes (__cdecl *DeviceGetPartNumberStrFuncPtr)(const char *portname, const unsigned char devId, char *partnumber, unsigned char *maxLen);
_deviceGetPartNumberStr = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('deviceGetPartNumberStr', NKTPDLL))
def deviceGetPartNumberStr(portname, devId):
	_readSize = c_ubyte(255)
	_readStr = create_string_buffer(_readSize.value)
	result = _deviceGetPartNumberStr(portname.encode('ascii'), devId, _readStr, _readSize)
	return result, _readStr.value

# \brief Returns the PCB version for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param PCBVersion Pointer to a preallocated unsigned char where the function will store the PCB version.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x62\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetPCBVersion(const char *portname, const unsigned char devId, unsigned char *PCBVersion);
#typedef DeviceResultTypes (__cdecl *DeviceGetPCBVersionFuncPtr)(const char *portname, const unsigned char devId, unsigned char *PCBVersion);
_deviceGetPCBVersion = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ubyte))(('deviceGetPCBVersion', NKTPDLL))
def deviceGetPCBVersion(portname, devId):
	_readValue = c_ubyte(0)
	result = _deviceGetPCBVersion(portname.encode('ascii'), devId, _readValue)
	return result, _readValue.value

# \brief Returns the status bits for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param statusBits Pointer to a preallocated unsigned short where the function will store the status bits.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x66\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetStatusBits(const char *portname, const unsigned char devId, unsigned long *statusBits);
#typedef DeviceResultTypes (__cdecl *DeviceGetStatusBitsFuncPtr)(const char *portname, const unsigned char devId, unsigned long *statusBits);
_deviceGetStatusBits = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ushort))(('deviceGetStatusBits', NKTPDLL))
def deviceGetStatusBits(portname, devId):
	_readValue = c_ulong(0)
	result = _deviceGetStatusBits(portname.encode('ascii'), devId, _readValue)
	return result, _readValue.value

# \brief Returns the error code for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param errorCode Pointer to a preallocated unsigned short where the function will store the error code.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x67\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetErrorCode(const char *portname, const unsigned char devId, unsigned short *errorCode);
#typedef DeviceResultTypes (__cdecl *DeviceGetErrorCodeFuncPtr)(const char *portname, const unsigned char devId, unsigned short *errorCode);
_deviceGetErrorCode = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ushort))(('deviceGetErrorCode', NKTPDLL))
def deviceGetErrorCode(portname, devId):
	_readValue = c_ushort(0)
	result = _deviceGetErrorCode(portname.encode('ascii'), devId, _readValue)
	return result, _readValue.value

# \brief Returns the bootloader version for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param version Pointer to a preallocated unsigned short where the function will store the bootloader version.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x6D\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetBootloaderVersion(const char *portname, const unsigned char devId, unsigned short *version);
#typedef DeviceResultTypes (__cdecl *DeviceGetBootloaderVersionFuncPtr)(const char *portname, const unsigned char devId, unsigned short *version);
_deviceGetBootloaderVersion = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ushort))(('deviceGetBootloaderVersion', NKTPDLL))
def deviceGetBootloaderVersion(portname, devId):
	_readValue = c_ushort(0)
	result = _deviceGetBootloaderVersion(portname.encode('ascii'), devId, _readValue)
	return result, _readValue.value

# \brief Returns the bootloader version (string) for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param versionStr Pointer to a preallocated string area where the function will store the bootloader version.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x6D\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetBootloaderVersionStr(const char *portname, const unsigned char devId, char *versionStr, unsigned char *maxLen);
#typedef DeviceResultTypes (__cdecl *DeviceGetBootloaderVersionStrFuncPtr)(const char *portname, const unsigned char devId, char *versionStr, unsigned char *maxLen);
_deviceGetBootloaderVersionStr = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('deviceGetBootloaderVersionStr', NKTPDLL))
def deviceGetBootloaderVersionStr(portname, devId):
	_readSize = c_ubyte(255)
	_readStr = create_string_buffer(_readSize.value)
	result = _deviceGetBootloaderVersionStr(portname.encode('ascii'), devId, _readStr, _readSize)
	return result, _readStr.value

# \brief Returns the firmware version for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param version Pointer to a preallocated unsigned short where the function will store the firmware version.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x64\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetFirmwareVersion(const char *portname, const unsigned char devId, unsigned short *version);
#typedef DeviceResultTypes (__cdecl *DeviceGetFirmwareVersionFuncPtr)(const char *portname, const unsigned char devId, unsigned short *version);
_deviceGetFirmwareVersion = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ushort))(('deviceGetFirmwareVersion', NKTPDLL))
def deviceGetFirmwareVersion(portname, devId):
	_readValue = c_ushort(0)
	result = _deviceGetFirmwareVersion(portname.encode('ascii'), devId, _readValue)
	return result, _readValue

# \brief Returns the firmware version (string) for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param versionStr Pointer to a preallocated string area where the function will store the firmware version.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x64\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetFirmwareVersionStr(const char *portname, const unsigned char devId, char *versionStr, unsigned char *maxLen);
#typedef DeviceResultTypes (__cdecl *DeviceGetFirmwareVersionStrFuncPtr)(const char *portname, const unsigned char devId, char *versionStr, unsigned char *maxLen);
_deviceGetFirmwareVersionStr = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('deviceGetFirmwareVersionStr', NKTPDLL))
def deviceGetFirmwareVersionStr(portname, devId):
	_readSize = c_ubyte(255)
	_readStr = create_string_buffer(_readSize.value)
	result = _deviceGetFirmwareVersionStr(portname.encode('ascii'), devId, _readStr, _readSize)
	return result, _readStr.value

# \brief Returns the Module serialnumber (string) for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param serialNumber Pointer to a preallocated string area where the function will store the serialnumber version.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x65\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetModuleSerialNumberStr(const char *portname, const unsigned char devId, char *serialNumber, unsigned char *maxLen);
#typedef DeviceResultTypes (__cdecl *DeviceGetModuleSerialNumberStrFuncPtr)(const char *portname, const unsigned char devId, char *serialNumber, unsigned char *maxLen);
_deviceGetModuleSerialNumberStr = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('deviceGetModuleSerialNumberStr', NKTPDLL))
def deviceGetModuleSerialNumberStr(portname, devId):
	_readSize = c_ubyte(255)
	_readStr = create_string_buffer(_readSize.value)
	result = _deviceGetModuleSerialNumberStr(portname.encode('ascii'), devId, _readStr, _readSize)
	return result, _readStr.value

# \brief Returns the PCB serialnumber (string) for a given device (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param serialNumber Pointer to a preallocated string area where the function will store the serialnumber version.
# \param maxLen Size of preallocated string area, modified by the function to reflect the actual length of the returned string. The returned string may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
# \note Register address 0x6E\n
#       It is not necessary to open the port, create the device or register before using this function, since it will do a dedicated read.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetPCBSerialNumberStr(const char *portname, const unsigned char devId, char *serialNumber, unsigned char *maxLen);
#typedef DeviceResultTypes (__cdecl *DeviceGetPCBSerialNumberStrFuncPtr)(const char *portname, const unsigned char devId, char *serialNumber, unsigned char *maxLen);
_deviceGetPCBSerialNumberStr = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('deviceGetPCBSerialNumberStr', NKTPDLL))
def deviceGetPCBSerialNumberStr(portname, devId):
	_readSize = c_ubyte(255)
	_readStr = create_string_buffer(_readSize.value)
	result = _deviceGetPCBSerialNumberStr(portname.encode('ascii'), devId, _readStr, _readSize)
	return result, _readStr.value



#*******************************************************************************************************
#* Callback - Device functions
#*******************************************************************************************************/
# Callback - Device functions
# Device functions primarly used in callback environments.

# \brief Creates a device in the internal devicelist. If the ::openPorts function has been called with the liveMode = 1 the kernel immediatedly starts to monitor the device.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param waitReady
#               \arg 0 Don't wait for the device being ready.
#               \arg 1 Wait up to 2 seconds for the device to complete its analyze cycle. (All standard registers being successfully read)
# \return A status result value ::DeviceResultTypes
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceCreate(const char *portname, const unsigned char devId, const char waitReady);
#typedef DeviceResultTypes (__cdecl *DeviceCreateFuncPtr)(const char *portname, const unsigned char devId, const char waitReady);
_deviceCreate = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte)(('deviceCreate', NKTPDLL))
def deviceCreate(portname, devId, waitReady):
	return _deviceCreate(portname.encode('ascii'), devId, waitReady)

# \brief Checks if a specific device already exists in the internal devicelist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param exists Pointer to an unsigned char where the function will store the exists status.
#               \arg 0 Device does not exists.
#               \arg 1 Device exists.
# \return A status result value ::DeviceResultTypes
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceExists(const char *portname, const unsigned char devId, unsigned char *exists);
#typedef DeviceResultTypes (__cdecl *DeviceExistsFuncPtr)(const char *portname, const unsigned char devId, unsigned char *exists);
_deviceExists = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ubyte))(('deviceExists', NKTPDLL))
def deviceExists(portname, devId):
        _exists = c_ubyte(0)
        result = _deviceExists(portname.encode('ascii'), devId, _exists)
        return result, _exists.value

# \brief Remove a specific device from the internal devicelist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \return A status result value ::DeviceResultTypes
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceRemove(const char *portname, const unsigned char devId);
#typedef DeviceResultTypes (__cdecl *DeviceRemoveFuncPtr)(const char *portname, const unsigned char devId);
_deviceRemove = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte)(('deviceRemove', NKTPDLL))
def deviceRemove(portname, devId):
	return _deviceRemove(portname.encode('ascii'), devId)

# \brief Remove all devices from the internal devicelist. No confirmation given, the list is simply cleared.
# \param portname Zero terminated string giving the portname (case sensitive).
# \return A status result value ::DeviceResultTypes
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceRemoveAll(const char *portname);
#typedef DeviceResultTypes (__cdecl *DeviceRemoveAllFuncPtr)(const char *portname);
_deviceRemoveAll = CFUNCTYPE(c_ubyte, c_char_p)(('deviceRemoveAll', NKTPDLL))
def deviceRemoveAll(portname):
	return _deviceRemoveAll(portname.encode('ascii'))

# \brief Returns a list with device types (module types) from the internal devicelist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param types Pointer to a preallocated area where the function stores the list of module types. The default list size is 256 bytes long (0-255) where each position indicates module address, containing 0 for no module or the module type for addresses having a module.\n
#  ex. 00h 61h 62h 63h 64h 65h 00h 00h 00h 00h 00h 00h 00h 00h 00h 60h 00h 00h etc.\n
# Indicates module type 61h at address 1, module type 62h at address 2 etc. and module type 60h at address 15
# \param maxTypes Pointer to an unsigned char giving the maximum number of types to retrieve.
#                 The returned list may be truncated to fit into the allocated area.
# \return A status result value ::DeviceResultTypes
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetAllTypes(const char *portname, unsigned char *types, unsigned char *maxTypes);
#typedef DeviceResultTypes (__cdecl *DeviceGetAllTypesFuncPtr)(const char *portname, unsigned char *types, unsigned char *maxTypes);
_deviceGetAllTypes = CFUNCTYPE(c_ubyte, c_char_p, POINTER(c_char), POINTER(c_ubyte))(('deviceGetAllTypes', NKTPDLL))
def deviceGetAllTypes(portname):
	_maxTypes = c_ubyte(255)
	_types = create_string_buffer(_maxTypes.value)
	result = _deviceGetAllTypes(portname.encode('ascii'), _types, _maxTypes)
	if result != 0: _maxTypes = c_ubyte(0)
	return result, _types.raw[:_maxTypes.value]

# \brief Returns the internal device mode for a specific device id (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId Given device id to retrieve device mode for.
# \param devMode Pointer to an unsigned char where the function stores the device mode. ::DeviceModeTypes
# \return A status result value ::DeviceResultTypes
# \note Requires the port being already opened with the ::openPorts function and the device being already created, either automatically or with the ::deviceCreate function.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetMode(const char *portname, const unsigned char devId, unsigned char *devMode);
#typedef DeviceResultTypes (__cdecl *DeviceGetModeFuncPtr)(const char *portname, const unsigned char devId, unsigned char *devMode);
_deviceGetMode = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ubyte))(('deviceGetMode', NKTPDLL))
def deviceGetMode(portname, devId):
        _devMode = c_ubyte(0)
        result = _deviceGetMode(portname.encode('ascii'), devId, _devMode)
        return result, _devMode.value

# \brief Returns the internal device live status for a specific device id (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId Given device id to retrieve liveMode.
# \param liveMode Pointer to an unsigned char where the function stores the live status.
#                 \arg 0 liveMode off
#                 \arg 1 liveMode on
# \return A status result value ::DeviceResultTypes
# \note Requires the port being already opened with the ::openPorts function and the device being already created, either automatically or with the ::deviceCreate function.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceGetLive(const char *portname, const unsigned char devId, unsigned char *liveMode);
#typedef DeviceResultTypes (__cdecl *DeviceGetLiveFuncPtr)(const char *portname, const unsigned char devId, unsigned char *liveMode);
_deviceGetLive = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_ubyte))(('deviceGetLive', NKTPDLL))
def deviceGetLive(portname, devId):
        _liveMode = c_ubyte(0)
        result = _deviceGetLive(portname.encode('ascii'), devId, _liveMode)
        return result, _liveMode.value

# \brief Sets the internal device live status for a specific device id (module address).
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId Given device id to set liveMode on.
# \param liveMode An unsigned char giving the new live status.
#                 \arg 0 liveMode off
#                 \arg 1 liveMode on
# \return A status result value ::DeviceResultTypes
# \note Requires the port being already opened with the ::openPorts function and the device being already created, either automatically or with the ::deviceCreate function.
#
#extern "C" NKTPDLL_EXPORT DeviceResultTypes deviceSetLive(const char *portname, const unsigned char devId, const unsigned char liveMode);
#typedef DeviceResultTypes (__cdecl *DeviceSetLiveFuncPtr)(const char *portname, const unsigned char devId, const unsigned char liveMode);
_deviceSetLive = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte)(('deviceSetLive', NKTPDLL))
def deviceSetLive(portname, devId, liveMode):
        return _deviceSetLive(portname.encode('ascii'), devId, liveMode)


#*******************************************************************************************************
#* Callback - Register functions
#*******************************************************************************************************/
# Callback - Register functions

# \brief Creates a register in the internal registerlist. If the ::openPorts function has been called with the liveMode = 1 the kernel immediatedly starts to monitor the register.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param priority The ::RegisterPriorityTypes (monitoring priority).
# \param dataType The ::RegisterDataTypes, not used internally but could be used in a common callback function to determine data type.
# \return A status result value ::RegisterResultTypes
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerCreate(const char *portname, const unsigned char devId, const unsigned char regId, const RegisterPriorityTypes priority, const RegisterDataTypes dataType);
#typedef RegisterResultTypes (__cdecl *RegisterCreateFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, const RegisterPriorityTypes priority, const RegisterDataTypes dataType);
_registerCreate = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, c_ubyte, c_ubyte)(('registerCreate', NKTPDLL))
def registerCreate(portname, devId, regId, priority, dataType):
        return _registerCreate(portname.encode('ascii'), devId, regId, priority, dataType)

# \brief Checks if a specific register already exists in the internal registerlist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \param exists Pointer to an unsigned char where the function will store the exists status.
#               \arg 0 Register does not exists.
#               \arg 1 Register exists.
# \return A status result value ::RegisterResultTypes
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerExists(const char *portname, const unsigned char devId, const unsigned char regId, unsigned char *exists);
#typedef RegisterResultTypes (__cdecl *RegisterExistsFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId, unsigned char *exists);
_registerExists = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte, POINTER(c_ubyte))(('registerExists', NKTPDLL))
def registerExists(portname, devId, regId):
        _exists = c_ubyte(0)
        result = _registerExists(portname.encode('ascii'), devId, regId, _exists)
        return result, _exists.value

# \brief Remove a specific register from the internal registerlist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regId The register id (register address).
# \return A status result value ::RegisterResultTypes
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerRemove(const char *portname, const unsigned char devId, const unsigned char regId);
#typedef RegisterResultTypes (__cdecl *RegisterRemoveFuncPtr)(const char *portname, const unsigned char devId, const unsigned char regId);
_registerRemove = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, c_ubyte)(('registerRemove', NKTPDLL))
def registerRemove(portname, devId, regId):
        return _registerRemove(portname.encode('ascii'), devId, regId)

# \brief Remove all registers from the internal registerlist. No confirmation given, the list is simply cleared.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \return A status result value ::RegisterResultTypes
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerRemoveAll(const char *portname, const unsigned char devId);
#typedef RegisterResultTypes (__cdecl *RegisterRemoveAllFuncPtr)(const char *portname, const unsigned char devId);
_registerRemoveAll = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte)(('registerRemoveAll', NKTPDLL))
def registerRemoveAll(portname, devId):
        return _registerRemoveAll(portname.encode('ascii'), devId)

# \brief Returns a list with register ids (register addresses) from the internal registerlist.
# \param portname Zero terminated string giving the portname (case sensitive).
# \param devId The device id (module address).
# \param regs Pointer to a preallocated area where the function stores the list of registers ids (register addresses).
# \param maxRegs Pointer to an unsigned char giving the maximum number of register ids to retrieve.
#                Modified by the function to reflect the actual number of register ids returned. The returned list may be truncated to fit into the allocated area.
# \return A status result value ::RegisterResultTypes
#
#extern "C" NKTPDLL_EXPORT RegisterResultTypes registerGetAll(const char *portname, const unsigned char devId, unsigned char *regs, unsigned char *maxRegs);
#typedef RegisterResultTypes (__cdecl *RegisterGetAllFuncPtr)(const char *portname, const unsigned char devId, unsigned char *regs, unsigned char *maxRegs);
_registerGetAll = CFUNCTYPE(c_ubyte, c_char_p, c_ubyte, POINTER(c_char), POINTER(c_ubyte))(('registerGetAll', NKTPDLL))
def registerGetAll(portname, devId):
	_maxRegs = c_ubyte(255)
	_regs = create_string_buffer(_maxTypes.value)
	result = _registerGetAll(portname.encode('ascii'), devId, _regs, _maxRegs)
	if result != 0: _maxRegs = c_ubyte(0)
	return result, _regs.raw[:_maxRegs.value]


#*******************************************************************************************************
#* Callback - Support functions
#*******************************************************************************************************/
# Callback - Support functions

# \brief Defines the PortStatusCallbackFuncPtr for the ::openPorts and ::closePorts functions.
# \param portname Zero terminated string giving the current portname.
# \param status The current port status as ::PortStatusTypes
# \param curScanAdr When status is ::PortScanProgress or ::PortScanDeviceFound this indicates the current module address scanned or found.
# \param maxScanAdr When status is ::PortScanProgress or ::PortScanDeviceFound this indicates the last module address to be scanned.
# \param foundType When status is ::PortScanDeviceFound this value will represent the found module type.
# \note Please note that due to risk of circular runaway leading to stack overflow, it is not allowed to call functions in the DLL from within the callback function.
# If a call is made to a function in the DLL the function will therefore return an application busy error.
#
#typedef void (__cdecl *PortStatusCallbackFuncPtr)(const char* portname,           // current port name
#                                                  const PortStatusTypes status,   // current port status
#                                                  const unsigned char curScanAdr, // current scanned address or device found address
#                                                  const unsigned char maxScanAdr, // total addresses to scan
#                                                  const unsigned char foundType); // device found type
portStatusCallbackFuncPtr = CFUNCTYPE(None, c_char_p, c_ubyte, c_ubyte, c_ubyte, c_ubyte)

# \brief Enables/Disables callback for port status changes.
# \param callback The ::PortStatusCallbackFuncPtr function pointer. Disable callbacks by parsing in a zero value.
#
#extern "C" NKTPDLL_EXPORT void setCallbackPtrPortInfo(PortStatusCallbackFuncPtr callback);
#typedef void (__cdecl *SetCallbackPtrPortInfoFuncPtr)(PortStatusCallbackFuncPtr callback);
_setCallbackPtrPortInfo = CFUNCTYPE(None, c_void_p)(('setCallbackPtrPortInfo', NKTPDLL))
def setCallbackPtrPortInfo(PortStatusCallback):
	_setCallbackPtrPortInfo(PortStatusCallback)


# \brief Defines the DeviceStatusCallbackFuncPtr for the devices created or connected with the ::deviceCreate function.
# \param portname Zero terminated string giving the current portname.
# \param devId The device id (module address).
# \param status The current port status as ::DeviceStatusTypes
# \note Please note that due to risk of circular runaway leading to stack overflow, it is not allowed to call functions in the DLL from within the callback function.
# If a call is made to a function in the DLL the function will therefore return an application busy error.
#
#typedef void (__cdecl *DeviceStatusCallbackFuncPtr)(const char* portname,                     // current port name
#                                                    const unsigned char devId,                // current device id
#                                                    const DeviceStatusTypes status,           // current device status
#                                                    const unsigned char devDataLen,           // number of bytes in devData
#                                                    const void* devData);                     // device data as specified in status
deviceStatusCallbackFuncPtr = CFUNCTYPE(None, c_char_p, c_ubyte, c_ubyte, c_ubyte, c_void_p)

# \brief Enables/Disables callback for device status changes.
# \param callback The ::DeviceStatusCallbackFuncPtr function pointer. Disable callbacks by parsing in a zero value.
#
#extern "C" NKTPDLL_EXPORT void setCallbackPtrDeviceInfo(DeviceStatusCallbackFuncPtr callback);
#typedef void (__cdecl *SetCallbackPtrDeviceInfoFuncPtr)(DeviceStatusCallbackFuncPtr callback);
_setCallbackPtrDeviceInfo = CFUNCTYPE(None, c_void_p)(('setCallbackPtrDeviceInfo', NKTPDLL))
def setCallbackPtrDeviceInfo(DeviceStatusCallback):
	_setCallbackPtrDeviceInfo(DeviceStatusCallback)


# \brief Defines the RegisterStatusCallbackFuncPtr for the registers created or connected with the ::registerCreate function.
# \param portname Zero terminated string giving the current portname.
# \param status The current register status as ::RegisterStatusTypes
# \param regType The ::RegisterDataTypes, not used internally but could be used in a common callback function to determine data type.
# \param regDataLen Number of databytes.
# \param regData The register data.
# \note Please note that due to risk of circular runaway leading to stack overflow, it is not allowed to to call functions in the DLL from within the callback function.
# If a call is made to a function in the DLL the function will therefore return an application busy error.
#
#typedef void (__cdecl *RegisterStatusCallbackFuncPtr)(const char* portname,                       // current port name
#                                                      const unsigned char devId,                  // current device id
#                                                      const unsigned char regId,                  // current device id
#                                                      const RegisterStatusTypes status,           // current register status
#                                                      const RegisterDataTypes regType,            // current register type
#                                                      const unsigned char regDataLen,             // number of bytes in regData
#                                                      const void *regData);                       // register data
registerStatusCallbackFuncPtr = CFUNCTYPE(None, c_char_p, c_ubyte, c_ubyte, c_ubyte, c_ubyte, c_ubyte, c_void_p)

# \brief Enables/Disables callback for register status changes.
# \param callback The ::RegisterStatusCallbackFuncPtr function pointer. Disable callbacks by parsing in a zero value.
#
#extern "C" NKTPDLL_EXPORT void setCallbackPtrRegisterInfo(RegisterStatusCallbackFuncPtr callback);
#typedef void (__cdecl *SetCallbackPtrRegisterInfoFuncPtr)(RegisterStatusCallbackFuncPtr callback);
_setCallbackPtrRegisterInfo = CFUNCTYPE(None, c_void_p)(('setCallbackPtrRegisterInfo', NKTPDLL))
def setCallbackPtrRegisterInfo(RegisterStatusCallback):
	_setCallbackPtrRegisterInfo(RegisterStatusCallback)


	
#print("ports = getAllPorts()")
#ports = getAllPorts()
#print("ports:" + ports)

#print("addResult = pointToPointPortAdd(\"MyPort2\", pointToPointPortData(\"192.168.1.90\",1080,\"192.168.1.91\",1080,1,50))")
#addResult = pointToPointPortAdd("MyPort2", pointToPointPortData("192.168.1.90",1080,"192.168.1.91",1080,1,50))
#print("addResult:", addResult)

#print("print(getAllPorts())")
#print(getAllPorts())

#print("getResult,getP2PData = pointToPointPortGet(\"MyPort2\")")
#getResult,getP2PData = pointToPointPortGet("MyPort2")
#print("getResult:", getResult)
#print("getP2PData:", getP2PData)

#print("print(getAllPorts())")
#print(getAllPorts())

#print("delResult = pointToPointPortDel(\"MyPort2\")")
#delResult = pointToPointPortDel("MyPort2")
#print("delResult:",delResult)

#print("print(getAllPorts())")
#print(getAllPorts())

#print("openResult = openPorts(\"COM43\", 1, 1)")
#openResult = openPorts("COM5", 1, 1)
#print("openResult:", openResult, PortResultTypes(openResult) )

#print("print(getOpenPorts())")
#print(getOpenPorts())

#print("readResult, readData = registerReadAscii(\"COM43\", 1, 0x69, 0)")
#readResult, readData = registerReadAscii("COM43", 1, 0x69, 0)
#print("readResult:",readResult)
#print("readData:",readData)

#print("writeResult = registerWrite(\"COM43\", 1, 0x69, bytes([0x41, 0x42, 0x43, 0x44, 0x45, 0x46]), 6, 0)")
#writeResult = registerWrite("COM43", 1, 0x69, bytes([0x41, 0x42, 0x43, 0x44, 0x45, 0x46]), 6, 0)
#print("writeResult:",writeResult, RegisterResultTypes(writeResult) )

#print("writeReadResult = registerWriteRead(\"COM43\", 1, 0x69, 0x45, 0)")
#writeReadResult, readData = registerWriteRead("COM43", 1, 0x69, bytes([0x45]), 1, 1)
#print("writeReadResult:",writeReadResult, RegisterResultTypes(writeReadResult) )
#print("readData:",readData)

#print("readResult, readData = registerReadAscii(\"COM43\", 1, 0x69, 0)")
#readResult, readData = registerReadAscii("COM43", 1, 0x69, 0)
#print("readResult:",readResult)
#print("readData:",readData)


#print("readResult, readData = registerReadU8(\"COM43\", 1, 0x61, 0)")
#readResult, readData = registerReadU8("COM43", 1, 0x66, 0)
#print("readResult:",readResult)
#print("readData:",readData)


#print("readResult, readData = registerReadS8(\"COM43\", 1, 0x61, 0)")
#readResult, readData = registerReadS8("COM43", 1, 0x66, 0)
#print("readResult:",readResult)
#print("readData:",readData)

#print("readResult, readData = registerReadAscii(\"COM43\", 1, 0x64, 2)")
#readResult, readData = registerReadAscii("COM43", 1, 0x64, 2)
#print("readResult:",readResult)
#print("readData:",readData)


#print(getOpenPorts())

