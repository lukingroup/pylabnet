import ctypes

class nanopositioners():


    def __init__(self):
        """ Instantiate nanopositiners"""

        #Load Nanopositioners DLL
        self._nanopositionersdll = ctypes.windll.LoadLibrary('SmarActCTL.dll')
        self._nanopositionersdll.SA_CTL_GetFullVersionString.restype = ctypes.c_char_p
        library_string = self._nanopositionersdll.SA_CTL_GetFullVersionString()
        library_str = library_string.decode("utf-8")
        print(library_str)

        #define arguments and results of C functions
        self._nanopositionersdll.SA_CTL_FindDevices.restype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_FindDevices.argtype = [ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_ulonglong)]

        # finding devices connected to controller
        # define C pointers
        buffer = ctypes.create_string_buffer(4096) #buffer is c_wchar, using byref in argument
        #buffer = ctypes.c_byte*4096
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer))
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, ctypes.POINTER(buffer),ctypes.POINTER(buffersize))
        print(library_str)

def main():
    nanpos = nanopositioners()

if __name__ == "__main__":

    main()




