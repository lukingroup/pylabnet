
import ctypes


class MPC320
    def __init__(self, logger=None):
        """ Instantiate Polarization controllers"""

        try
# Loads polarization contorolles DLL and define arguments and result types for c function
            self._polarizationdll = ctypes.windll.LoadLibrary('Thorlabs.Motion.Control.Polarizer.dll')
            self._configure_functions()

# Build list of connected device
            testSerialNo = ctypes.create_string_buffer[16]  #the way to have a mutable buffer
            testSerialNoSize = ctypes.c_size_t(ctypes.sizeof(testSerialNo)) #size _t gives c_ulonglong, not as in manual
            serialNo = _wtoi(argv[1])
            testSerialNo =  "A= %d\n, B = %s\n, " % (testSerialNoSize, serialNo)
            print(testSerialNo)

# Get device list size
            if (self._polarizationdll.TLI_BuildDeviceList() == 0)
                devicelist = self._polarizationdll.TLI_GetDeviceListSize()
                n = ctypes.c_short
                n = self._polarizationdll.TLI_GetDeviceListSize()

# get MPCx20 serial numbers
                serialNos = ctypes.c_char[100]
                self._polarizationdll.TLI_GetDeviceListByTypeExt(serialNos, 100, 38)
                ctypes.c_char = searchContext
                # for sure somthing else in left side 
                ctypes.c_char_p = "A= %d\n, B = %s\n, " % (serialNos, &searchContext)

                searchContext = ctypes.c_char_p
                p = ctypes.c_char_p 
                p ="A= %d\n, B = %s\n, " % (serialNos, searchContext)
                               
#get device info from device
                #define strcuture of DeviceInfo as in hedear file
                TLI_DeviceInfo deviceInfo
                self._polarizationdll.TLI_GetDeviceInfo(p, deviceInfo)



            serial_number = ctypes.wintypse.DWORd /  ctypes.c_char_p 


def _configure_functions(self):
        """ Defines arguments and results for c functions """


             self._polarizationdll.TLI_BuildDeviceList()
             self._polarizationdll.TLI_GetDeviceListSize.restype = ctype.c_short
             self._polarizationdll.TLI_MPC_GetPolParams(char const * serialNo, PolarizerParameters *polParams);
             
             self._polarizationdll.TLI_MPC_Open.argtype = ctypes.c_char_p
             self._polarizationdll.TLI_MPC_Open.restype = ctypes.c_short
             self._polarizationdll.TLI_MPC_Close.argtype = ctypes.c_char_p 
             self._polarizationdll.TLI_MPC_Close.restype = ctypes.c_void_p
             self._polarizationdll.TLI_MPC_CheckConnection.argtype = ctypes.c_char_p
             self._polarizationdll.TLI_MPC_CheckConnection.restype = ctypes.c_bool           
             self._polarizationdll.TLI_MPC_Identify.argtype = ctype.c_char_p
             self._polarizationdll.TLI_MPC_Identify.restype = ctype.c_void_p
             self._polarizationdll.TLI_MPC_MoveRelative.argtype = [ctypes.c_char_p , ctypes.c_int16,ctypes.c_double] #int16 is POL paddle, where different numbers for differnet paddles
             self._polarizationdll.TLI_MPC_MoveRelative.restype = ctypes.c_short



