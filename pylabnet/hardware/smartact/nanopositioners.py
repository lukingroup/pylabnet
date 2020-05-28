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

        # finding devices connected to controlle
        buffer = ctypes.create_string_buffer(4096)  #the way to have a mutable buffer
        #buffer = ctypes.c_byte*4096
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer)) #size _t gives c_ulonglong, not as in manual
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, ctypes.pointer(buffer),ctypes.pointer(buffersize))
        print(library_str)  #for debugging with breakpoint here

def main():
    nanpos = nanopositioners()

if __name__ == "__main__":

    main()




