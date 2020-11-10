
import ctypes
from ctypes import wintypes
from comtypes.typeinfo import SAFEARRAYABOUND

# define DEviceInfo strcuture
class TVI_DeviceInfo(Structure):
    _fields_ = [("typeID",c_dword)
                ("description" (65*c_char))
                ("serialNo", (9*c_char))
                ("PID", c_dword)
                ("isKnownType", c_bool)
                ("motorType", MOT_MotorTypes) 
                ("isPiezoDevice", c_bool)
		        ("isLaser", c_bool)
		        ("isCustomType", c_bool)
                ("isCustomType", c_bool)
                ("isRack", c_bool)
                ("maxChannels", c_short)
                ("maxPaddles", c_short)]

class PolarizerParameters(Structure):
    _fields_ = [("Velocity", c_ushort)
                ("HomePosition", c_double)
                ("JogSize1", c_double)
                ("JogSize2", c_double)
                ("JogSize3", c_double)]

#class SAFEARRAY (structure)
#    _fields_ [("cDims")]

class MPC320:
    def __init__(self, logger=None):
        """ Instantiate Polarization controllers"""

        try
            # Loads polarization contorolles DLL and define arguments and result types for c function
            self._polarizationdll = ctypes.windll.LoadLibrary('Thorlabs.MotionControl.PolarizerCLI.dll')   
            self._devmanagerdll = ctypes.windll.LoadLibrary('Thorlabs.MotionControl.DeviceManagerCLI.dll')
            self._configure_functions()

            # Get devices serial numbers
            SerialNos = ctypes.create_string_buffer[16]  #the way to have a mutable buffer
            SerialNosSize = wintype.DWORD(ctypes.sizeof( SerialNos)) #size _t gives c_ulonglong, not as in manual
            return = self._polarizationdll.TLI_GetDeviceListByTypeExt(SerialNos, SerialNosSize, self._TVI_DeviceInfo.typeID)

            if return:
                 print("Failed to get device list")
            else:
                print("Device line created succesfully") #change these massages to interact with logger
            
            #get device info
            self._polarizationdll.TLI_GetDeviceInfo(SerialNos, ctypes.POINTER(self._TLI_DeviceInfo))
            print("found devices:" {self._TLI_DeviceInfo.description} {self._TLI_DeviceInfo.serialNo} )
            print("self._TLI_DeviceInfo.serialNo")
            
            # how to pick a specific device?
            #Establishe connection to device
            result = self._polarizationdll.TLI.MPC_Open(ctypes.POINTER(self._TLI_DeviceInfo.serialNo))
            if (result == 0):
                print("Connected succesfully to device")
            else:
                print("a problem occured when trying to connect to device")

            

            #serialNo = _wtoi(argv[1])
            #testSerialNo =  "A= %d\n, B = %s\n, " % (testSerialNoSize, serialNo)
            #print(testSerialNo)

            #get MPCx20 serial numbers
                
            ctypes.c_char = searchContext
            #for sure somthing else in left side 
            #ctypes.c_char_p = "A= %d\n, B = %s\n, " % (serialNos, &searchContext)
            #searchContext = ctypes.c_char_p
            #p = ctypes.c_char_p 
            #p ="A= %d\n, B = %s\n, " % (serialNos, searchContext)

            
                
           
            
                


            serial_number = ctypes.wintypse.DWORd /  ctypes.c_char_p 


def _configure_functions(self):
        """ Defines arguments and results for c functions """



             self._polarizationdll.TLI_BuildDeviceList()
             self._polarizationdll.TLI_GetDeviceListSize.restype = ctype.c_short
             self._polarizationdll.TLI_GetDeviceInfo.argtypes = [ctypes.POINTER(c_char), ctypes.POINTER(TLI_DeviceInfo)]
             self._polarizationdll.TLI_GetDeviceInfo.restype = #?
             self._polarizationdll.TLI_GetDeviceList.restype = ctypes.POINTER(POINTER(safearray))
             self._polarizationdll.TLI_GetDeviceList.restype = ctypes.POINTER(POINTER(safearray))
            self._polarizationdll.TLI_GetDeviceListByTypeExt.argtypes =[ctypes.POINTER(ctypes.c_char), .wintypes.DWORD ctypes.c_int)
             self._polarizationdll.TLI_GetDeviceListByTypeExt.restype = ctypes.POINTER(POINTER(safearray)) 
            
             
             self._polarizationdll.TLI_MPC_Open.argtype = ctypes.POINTER(c_char)
             #self._polarizationdll.TLI_MPC_Open.restype = ctypes.c_short  ?
             self._polarizationdll.TLI_MPC_Close.argtype = ctypes.POINTER(c_char)
             #self._polarizationdll.TLI_MPC_Close.restype = ctypes.c_void_p  ?
             self._polarizationdll.TLI_MPC_CheckConnection.argtype = ctypes.c_char_p
             self._polarizationdll.TLI_MPC_CheckConnection.restype = ctypes.c_bool           
             self._polarizationdll.TLI_MPC_Identify.argtype = ctype.c_char_p
             self._polarizationdll.TLI_MPC_Identify.restype = ctype.c_void_p
             self._polarizationdll.TLI_MPC_GetPolParams.argtypes = [ctypes.c_char_p, ctypes.POINTER(PolarizerParameters)] 
                        
             self._polarizationdll.TLI_MPC_MoveRelative.argtype = [ctypes.c_char_p , ctypes.c_int16,ctypes.c_double] #int16 is POL paddle, where different numbers for differnet paddles
             self._polarizationdll.TLI_MPC_MoveRelative.restype = ctypes.c_short



