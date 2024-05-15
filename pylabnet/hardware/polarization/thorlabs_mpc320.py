""" Module for controlling Thorlabs motorized pollarization paddles """
import ctypes
from ctypes import Structure
import time
from pylabnet.utils.logging.logger import LogHandler
import os

#from comtypes.typeinfo import SAFEARRAYABOUND

#enum FT_Status
FT_OK = ctypes.c_short(0x00)
FT_InvalidHandle = ctypes.c_short(0x0)
FT_DeviceNotFound = ctypes.c_short(0x02)
FT_DeviceNotOpened = ctypes.c_short(0x03)
FT_IOError = ctypes.c_short(0x04)
FT_InsufficientResources = ctypes.c_short(0x05)
FT_InvalidParameter = ctypes.c_short(0x06)
FT_DeviceNotPresent = ctypes.c_short(0x07)
FT_IncorrectDevice = ctypes.c_short(0x08)
FT_Status = ctypes.c_short

#enum MOT_MotorTypes
MOT_NotMotor = ctypes.c_int(0)
MOT_DCMotor = ctypes.c_int(1)
MOT_StepperMotor = ctypes.c_int(2)
MOT_BrushlessMotor = ctypes.c_int(3)
MOT_CustomMotor = ctypes.c_int(100)
MOT_MotorTypes = ctypes.c_int

#enum POL_Paddle
paddle1 = ctypes.c_uint16(1)
paddle2 = ctypes.c_uint16(2)
paddle3 = ctypes.c_uint16(3)
POL_Paddles = ctypes.c_uint16

#enum POL_PaddleBits
none_ctype = ctypes.c_ushort(0x0)   #is None in header file
PaddleBit1 = ctypes.c_ushort(0x01)
PaddleBit2 = ctypes.c_ushort(0x02)
PaddleBit4 = ctypes.c_ushort(0x04)
AllPaddles = ctypes.c_ushort(0x07)
POL_PaddleBits = ctypes.c_ushort

#enum MOT_TravelDirection
MOT_TravelDirectionDisabled = ctypes.c_short(0x00)
MOT_Forwards = ctypes.c_short(0x01)
MOT_Reverse = ctypes.c_short(0x02)
MOT_TravelDirection = ctypes.c_short

#enum MPC_IOModes
MPC_ToggleOnPositiveEdge = ctypes.c_ulong(0x01)
MPC_SetPositionOnPositiveEdge = ctypes.c_ulong(0x02)
MPC_OutputHighAtSetPosition = ctypes.c_ulong(0x04)
MPC_OutputHighWhemMoving = ctypes.c_ulong(0x08)
MPC_IOModes = ctypes.c_ulong


class TLI_DeviceInfo(Structure):
    _fields_ = [("typeID", ctypes.c_ulong),
                ("description", (65 * ctypes.c_char)), #changed from 65* _char
                ("serialNo", (9 * ctypes.c_char)), #changed from 9* _char
                ("PID", ctypes.c_ulong),# wintypes.DWORD
                ("isKnownType", ctypes.c_bool),
                ("motorType", MOT_MotorTypes),
                ("isPiezoDevice", ctypes.c_bool),
                ("isLaser", ctypes.c_bool),
                ("isCustomType", ctypes.c_bool),
                ("isRack", ctypes.c_bool),
                ("maxPaddles", ctypes.c_short)]

# class TLI_HardwareInformation(Structure):
#    _fields_ = [("serialNumber", ctypes.c_ulong),
#               ("modelNumber", (8 * ctypes.c_char)),
#                ("type",  ctypes.c_ushort),
#                ("firmwareVersion", ctypes.c_ulong),
#                ("notes", (48 * ctypes.c_char)),
#                ("deviceDependantData", (12 * ctypes.c_byte)),
#                ("hardwareVersion",  ctypes.c_ushort),
#                ("modificationState",  ctypes.c_ushort),
#                ("numChannels", ctypes.c_ushort)]


class TLI_PolarizerParameters(Structure):
    _fields_ = [("Velocity", ctypes.c_ushort),
                ("HomePosition", ctypes.c_double),
                ("JogSize1", ctypes.c_double),
                ("JogSize2", ctypes.c_double),
                ("JogSize3", ctypes.c_double)]

#class SAFEARRAYBOUND(Strcuture):
#    _fields_ = [("cElements" , ctypes.c_ulong),
 #               ("lLbound" , ctypes.c_long)]

#class SAFEARRAY(Strcuture):
#    _fields_ = [("cDims", ctypes.c_ushort),
#                ("fFeatures", ctypes.c_ushort),
#                ("cbElements", ctypes.c_ulong),
#                ("cLocks", ctypes.c_ulong),
#                ("pvData", ctypes.c_void_p),
#                ("rgsabound", SAFEARRAYBOUND * 1)]


class Driver():

    def __init__(self, device_num, logger):
        """Instantiate driver class.

        device_num is numbering of devices connected via USB. Drivrt then finds serial numbers of polarization paddle by Driver, e.g. b'38154354' """

        # Instantiate log.
        self.log = LogHandler(logger=logger)
        #Loads polarization contorolles DLL and define arguments and result 5types for c function

        dllabspath_pol = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "Thorlabs.MotionControl.Polarizer.dll"
        dllabspath_dm = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "Thorlabs.MotionControl.DeviceManager.dll"

        self._polarizationdll = ctypes.cdll.LoadLibrary(dllabspath_pol)
        self._devmanagerdll = ctypes.cdll.LoadLibrary(dllabspath_dm)
        self._configure_functions()

        #get device list size
        if self._polarizationdll.TLI_BuildDeviceList() == 0:
            num_devs = self._polarizationdll.TLI_GetDeviceListSize()
            #print(f"There are {num_devs} devices connected")

        #Get devices serial numbers
        serialNos = ctypes.create_string_buffer(100) #the way to have a mutable buffer
        serialNosSize = ctypes.c_ulong(ctypes.sizeof(serialNos))
        List = self._polarizationdll.TLI_GetDeviceListByTypeExt(serialNos, serialNosSize, 38)

        #if List:
        #    print("Failed to get device list")
        #else:
        #    print("Device list created succesfully") #change these massages to interact with logger

        self.dev_name = serialNos.value.decode("utf-8") #.strip().split(',')
        #print(f"Connected to device {self.dev_name}")

        #get device info including serial number
        self.device_info = TLI_DeviceInfo()  # container for device info
        self._polarizationdll.TLI_GetDeviceInfo(serialNos[(device_num - 1) * 9:(device_num * 9) - 1], ctypes.byref(self.device_info)) #when there will be a few devices figure out how to seperate and access each one
        self.device = serialNos[(device_num - 1) * 9:(device_num * 9) - 1]

        #print("Description: ", self.device_info.description)
        #print("Serial No: ", self.device_info.serialNo)
        #print("Motor Type: ", self.device_info.motorType)
        #print("USB PID: ", self.device_info.PID)
        #print("Max Number of Paddles: ", self.device_info.maxPaddles)

        #establising connection to device
        self.paddles = [paddle1, paddle3, paddle2]

        connection = self._polarizationdll.MPC_Open(self.device)
        if connection == 0:
            self.log.info(f"Successfully connected to {self.device}.")
        else:
            self.log.error(f"Connection to {self.device} failed due to error {connection}.")

    #technical methods

    def _configure_functions(self):
        """ Defines arguments and results for c functions """

        self._polarizationdll.TLI_BuildDeviceList.argtype = None
        self._polarizationdll.TLI_BuildDeviceList.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceListSize.argtype = None
        self._polarizationdll.TLI_GetDeviceListSize.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceInfo.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_DeviceInfo)]
        self._polarizationdll.TLI_GetDeviceInfo.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceListByTypeExt.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_ulong, ctypes.c_int]
        self._polarizationdll.TLI_GetDeviceListByTypeExt.restype = ctypes.c_short
        self._polarizationdll.MPC_Open.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_Open.restype = ctypes.c_short
        self._polarizationdll.MPC_Close.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_Close.restype = ctypes.c_short
        self._polarizationdll.MPC_CheckConnection.argtype = ctypes.c_char_p
        self._polarizationdll.MPC_CheckConnection.restype = ctypes.c_bool
        self._polarizationdll.MPC_GetPosition.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_GetPosition.restype = ctypes.c_double
        self._polarizationdll.MPC_RequestPolParams.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_RequestPolParams.restype = ctypes.c_short
        self._polarizationdll.MPC_GetPolParams.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters)]
        self._polarizationdll.MPC_GetPolParams.restype = ctypes.c_short
        self._polarizationdll.MPC_SetPolParams.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters)]
        self._polarizationdll.MPC_SetPolParams.restype = ctypes.c_short
        self._polarizationdll.MPC_SetJogSize.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_SetJogSize.restype = ctypes.c_short
        self._polarizationdll.MPC_Jog.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, MOT_TravelDirection]
        self._polarizationdll.MPC_Jog.restype = ctypes.c_short
        self._polarizationdll.MPC_GetMaxTravel.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_GetMaxTravel.restype = ctypes.c_double
        self._polarizationdll.MPC_MoveToPosition.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_MoveToPosition.restype = ctypes.c_short
        self._polarizationdll.MPC_Stop.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_Stop.restype = ctypes.c_short
        self._polarizationdll.MPC_Home.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_Home.restype = ctypes.c_short
        self._polarizationdll.MPC_Jog.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters), MOT_TravelDirection]
        self._polarizationdll.MPC_Jog.restype = ctypes.c_short
        self._polarizationdll.MPC_StartPolling.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_int]
        self._polarizationdll.MPC_StartPolling.restype = ctypes.c_bool
        self._polarizationdll.MPC_StopPolling.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_StopPolling.restype = ctypes.c_void_p #did not find the a c_void with no pointer as needed
        self._polarizationdll.MPC_SetVelocity.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_short]
        self._polarizationdll.MPC_SetVelocity.restype = ctypes.c_short
        self._polarizationdll.MPC_MoveRelative.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_MoveRelative.restype = ctypes.c_short
        self._polarizationdll.MPC_GetStepsPerDegree.argtype = [ctypes.POINTER(ctypes.c_char)]
        self._polarizationdll.MPC_GetStepsPerDegree.result = ctypes.c_double

        #wrap function for external use

    def open(self):
        result = self._polarizationdll.MPC_Open(self.device)
        if result == 0:
            print("Connected succesfully to device")
        else:
            print("A problem occured when trying to connect to device")

    def close(self):
        resultc = self._polarizationdll.MPC_Close(self.device)
        if resultc == 0:
            print("Closed connection to device")
        else:
            print("A problem occured when trying to diconnect from device")

    def home(self, paddle_num):
        home_result = self._polarizationdll.MPC_Home(self.device, self.paddles[paddle_num])

        return home_result

    def set_velocity(self, velocity):
        velocity = self._polarizationdll.MPC_SetVelocity(self.device, velocity)

    def move(self, paddle_num, pos, sleep_time):
        #posinitial = self._polarizationdll.MPC_GetPosition(self.device,  self.paddles[paddle_num])
        move_result = self._polarizationdll.MPC_MoveToPosition(self.device, self.paddles[paddle_num], pos)
        time.sleep(abs(sleep_time * pos / 170))
        #posfinal = self._polarizationdll.MPC_GetPosition(self.device, self.paddles[paddle_num])

        return move_result #, posinitial, posfinal

    def move_rel(self, paddle_num, step, sleep_time=0.1):
        #posinitial = self._polarizationdll.MPC_GetPosition(self.device, self.paddles[paddle_num])
        move_result = self._polarizationdll.MPC_MoveRelative(self.device, self.paddles[paddle_num], step)
        time.sleep(abs(sleep_time * step / 170))
        #posfinal = self._polarizationdll.MPC_GetPosition(self.device, self.paddles[paddle_num])

        return move_result #, posinitial, posfinal

    def get_angle(self, paddle_num):
        currentpos = self._polarizationdll.MPC_GetPosition(self.device, self.paddles[paddle_num])

        return currentpos


if __name__ == "__main__":

    import os
    from pylabnet.utils.logging.logger import LogClient

    device_id = 1

    # Instantiate logger.
    logger = LogClient(
        host='10.250.194.110',
        port=27957,
        module_tag=f'Pol Paddle'
    )

    pol = Driver(device_num=device_id, logger=logger)

    pol.move_rel(0, 50)
    pol.move_rel(1, 78)
    pol.move_rel(2, 90)
