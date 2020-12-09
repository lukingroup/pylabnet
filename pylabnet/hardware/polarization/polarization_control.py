""" Module for controlling Thorlabs motorized pollarization paddles """

import ctypes
from ctypes import wintypes
from ctypes import Structure
import time
#from comtypes.typeinfo import SAFEARRAYABOUND

#enum FT_Status
FT_OK = ctypes.c_short(0x00)
FT_InvalidHandle = ctypes.c_short(0x0)
FT_DeviceNotFound = ctypes.c_short(0x02)
FT_DeviceNotOpened = ctypes.c_short(0x03)
FT_IOError = ctypes.c_short(0x04)
FT_InsufficientResources =  ctypes.c_short(0x05)
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
PaddleBit1 =  ctypes.c_ushort(0x01)
PaddleBit2 = ctypes.c_ushort(0x02)
PaddleBit4= ctypes.c_ushort(0x04)
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
                ("description", (65* ctypes.c_char)), #changed from 65* _char 
                ("serialNo", (9* ctypes.c_char)), #changed from 9* _char 
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

class MPC320:
    def __init__(self):
        """ Instantiate Polarization controllers"""
     
        #Loads polarization contorolles DLL and define arguments and result 5types for c function
        self._polarizationdll = ctypes.cdll.LoadLibrary('Thorlabs.MotionControl.Polarizer.dll')  
        self._devmanagerdll = ctypes.cdll.LoadLibrary('Thorlabs.MotionControl.DeviceManager.dll')
        self._configure_functions()

        #get device list size
        if self._polarizationdll.TLI_BuildDeviceList() == 0:
            num_devs = self._polarizationdll.TLI_GetDeviceListSize()
            print(f"There are {num_devs} devices connected")    
        
        #Get devices serial numbers
        serialNos = ctypes.create_string_buffer(100) #the way to have a mutable buffer
        serialNosSize = ctypes.c_ulong(ctypes.sizeof(serialNos)) 
        List = self._polarizationdll.TLI_GetDeviceListByTypeExt(serialNos, serialNosSize, 38)

        if List:
            print("Failed to get device list")
        else:
            print("Device list created succesfully") #change these massages to interact with logger

        self.dev_name = serialNos.value.decode("utf-8") #.strip().split(',')
        print(f"Connected to device {self.dev_name}")

        #get device info including serial number
        device_info = TLI_DeviceInfo()  # container for device info
        self._polarizationdll.TLI_GetDeviceInfo(serialNos[0:8], ctypes.byref(device_info)) #when there will be a few devices figure out how to seperate and access each one

        print("Description: ", device_info.description)
        print("Serial No: ", device_info.serialNo)
        print("Motor Type: ", device_info.motorType)
        print("USB PID: ", device_info.PID)
        print("Max Number of Paddles: ", device_info.maxPaddles)

        # how to pick a specific device?
        #Establishe connection to device
        result = self._polarizationdll.MPC_Open(device_info.serialNo)
        if result == 0:
            print("Connected succesfully to device")
        else:
            print("A problem occured when trying to connect to device")
        
        Stepperdegree = self._polarizationdll.MPC_GetStepsPerDegree(device_info.serialNo)
        maxtravel = self._polarizationdll.MPC_GetMaxTravel(device_info.serialNo)
        #Jog paddle
        #TLI_PolarizerParameters.JogSize1 = ctypes.c_double(10)
        #startjog2 = self._polarizationdll.MPC_StartPolling(device_info.serialNo, 200)
        #if startjog2 == True:
        #    print(f"succefully started polling of device {device_info.serialNo}")
        #else:
        #    print(f"A problem occured when trying to start polling of device {device_info.serialNo}")
        #home2 = self._polarizationdll.MPC_Home(device_info.serialNo, paddle1)
        #self.PosJogI = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle1)
        #print(f"Position before jog is {self.PosJogI}")  
        #self._polarizationdll.MPC_SetJogSize(device_info.serialNo, paddle1, ctypes.c_double(1))
        #time.sleep(20)
        #self._polarizationdll.MPC_Jog(device_info.serialNo, paddle1 , MOT_Forwards)
        #self.PosJogF = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle2)
        #print(f"Position after jog is {self.PosJogF}")
        #self._polarizationdll.MPC_StopPolling(device_info.serialNo)

        #define parameters for movement
        paddle = paddle2
        stepsize = 45 #degrees
        stepnum = 1
        initialpos = maxtravel

        #38159764 - fiber device out
        #Move paddles
        home = self._polarizationdll.MPC_Home(device_info.serialNo, paddle)
        self.PosI = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle)
        print(f"Position before move is {self.PosI}")    
        #move = self._polarizationdll.MPC_MoveToPosition(device_info.serialNo, paddle1, 50.0)
        #time.sleep(20)
        #self.PosF = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle1)
        #print(f"Position after move is {self.PosF}")  
        move = self._polarizationdll.MPC_MoveToPosition(device_info.serialNo, paddle, initialpos) 
        time.sleep(100)
        self.PosIn = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle)
        print(f"Moved to initial position: {self.PosIn}")  

        for step in range(1, stepnum, stepsize):
            mover = self._polarizationdll.MPC_MoveRelative(device_info.serialNo, paddle, stepsize) 
            time.sleep(1)
            self.PosF = self._polarizationdll.MPC_GetPosition(device_info.serialNo, paddle)
            print(f"Position after move relative is {self.PosF}")  
        self._polarizationdll.MPC_StopPolling(device_info.serialNo)
        
        #closes connection to device
        self._polarizationdll.MPC_Close(device_info.serialNo)

    #technical methods

    def _configure_functions(self):
        """ Defines arguments and results for c functions """

        self._polarizationdll.TLI_BuildDeviceList.argtype = None
        self._polarizationdll.TLI_BuildDeviceList.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceListSize.argtype = None
        self._polarizationdll.TLI_GetDeviceListSize.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceInfo.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_DeviceInfo)]
        self._polarizationdll.TLI_GetDeviceInfo.restype = ctypes.c_short
        self._polarizationdll.TLI_GetDeviceListByTypeExt.argtypes =[ctypes.POINTER(ctypes.c_char),ctypes.c_ulong, ctypes.c_int]
        self._polarizationdll.TLI_GetDeviceListByTypeExt.restype = ctypes.c_short      
        self._polarizationdll.MPC_Open.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_Open.restype = ctypes.c_short
        self._polarizationdll.MPC_Close.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_Close.restype = ctypes.c_short
        self._polarizationdll.MPC_CheckConnection.argtype = ctypes.c_char_p
        self._polarizationdll.MPC_CheckConnection.restype = ctypes.c_bool           
        #self._polarizationdll.TLI_MPC_Identify.argtype = ctype.c_char_p
        #self._polarizationdll.TLI_MPC_Identify.restype = ctype.c_void_p
        self._polarizationdll.MPC_GetPosition.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_GetPosition.restype = ctypes.c_double
        self._polarizationdll.MPC_RequestPolParams.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_RequestPolParams.restype = ctypes.c_short
        self._polarizationdll.MPC_GetPolParams.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters)] 
        self._polarizationdll.MPC_GetPolParams.restype = ctypes.c_short 
        self._polarizationdll.MPC_SetPolParams.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters)]
        self._polarizationdll.MPC_SetPolParams.restype = ctypes.c_short
        #self._polarizationdll.MPC_GetJogSize.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters)]
        #self._polarizationdll.MPC_GetJogSize.restype = ctypes.c_double
        self._polarizationdll.MPC_SetJogSize.argtypes =  [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_SetJogSize.restype =  ctypes.c_short
        self._polarizationdll.MPC_Jog.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, MOT_TravelDirection]
        self._polarizationdll.MPC_Jog.restype = ctypes.c_short
        self._polarizationdll.MPC_GetMaxTravel.argtype = ctypes.POINTER(ctypes.c_char)
        self._polarizationdll.MPC_GetMaxTravel.restype = ctypes.c_double
        self._polarizationdll.MPC_MoveToPosition.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_MoveToPosition.restype = ctypes.c_short
        self._polarizationdll.MPC_Stop.argtypes =  [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_Stop.restype = ctypes.c_short
        self._polarizationdll.MPC_Home.argtypes =  [ctypes.POINTER(ctypes.c_char), POL_Paddles]
        self._polarizationdll.MPC_Home.restype = ctypes.c_short
        self._polarizationdll.MPC_Jog.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(TLI_PolarizerParameters), MOT_TravelDirection]
        self._polarizationdll.MPC_Jog.restype = ctypes.c_short
	    #self._polarizationdll.MPC_SetJogSize.argtypes = [ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
	    #self._polarizationdll.MPC_SetJogSize.restype = ctypes.c_short
        self._polarizationdll.MPC_StartPolling.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_int]
        self._polarizationdll.MPC_StartPolling.restype = ctypes.c_bool
        self._polarizationdll.MPC_StopPolling.argtype = ctypes.POINTER(ctypes.c_char)   
        self._polarizationdll.MPC_StopPolling.restype = ctypes.c_void_p #did not find the a c_void with no pointer as needed
        self._polarizationdll.MPC_SetVelocity.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_short]
        self._polarizationdll.MPC_SetVelocity.restype = ctypes.c_short
        self._polarizationdll.MPC_MoveRelative.argtypes =[ctypes.POINTER(ctypes.c_char), POL_Paddles, ctypes.c_double]
        self._polarizationdll.MPC_MoveRelative.restype = ctypes.c_short
        self._polarizationdll.MPC_GetStepsPerDegree.argtype = [ctypes.POINTER(ctypes.c_char)]
        self._polarizationdll.MPC_GetStepsPerDegree.result = ctypes.c_double

def main():
    mpc = MPC320()

if __name__ == "__main__":
    main() 

