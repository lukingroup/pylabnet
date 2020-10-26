
import ctypes



class MPC320

 # Loads Nanopositioners DLL and define arguments and result types for c function
            self._polarizationdll = ctypes.windll.LoadLibrary('Thorlabs.Motion.Control.Polarizer.dll')
            self._configure_functions()


            serial_number = ctypes.wintypse.DWORd /  ctypes.c_char_p 


def _configure_functions(self):
        """ Defines arguments and results for c functions """


             self._polarizationdll.TLI_BuildDeviceList()
             self._polarizationdll.TLI_GetDeviceListSize()
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



