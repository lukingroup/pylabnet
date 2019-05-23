import ctypes
from hardware.ni_hsdio.c_headers import NITypes, NIConst, build_c_func_prototypes
import numpy as np
import copy


class NI654x:
    def __init__(self, dev_name_str, dll_path_str):

        # "Load" niHSDIO DLL
        self.dll = ctypes.WinDLL(dll_path_str)

        # Build prototypes (in particular, specify the return
        # types such that Python reads results correctly)
        build_c_func_prototypes(self.dll)



        pass




