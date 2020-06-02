import ctypes

class Nanopositioners():

    def __init__(self):
        """ Instantiate Nanopositiners"""

        #Load Nanopositioners DLL
        self._nanopositionersdll = ctypes.windll.LoadLibrary('SmarActCTL.dll')
        self._nanopositionersdll.SA_CTL_GetFullVersionString.restype = ctypes.c_char_p
        library_string = self._nanopositionersdll.SA_CTL_GetFullVersionString()
        library_str = library_string.decode("utf-8")
        print(library_str)

        #define arguments and results of C functions
        self._nanopositionersdll.SA_CTL_FindDevices.restype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_FindDevices.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_ulonglong)]

        #finding devices connected to controller
        buffer = ctypes.create_string_buffer(4096)  #the way to have a mutable buffer
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer)) #size _t gives c_ulonglong, not as in manual
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, buffer,buffersize)
        buffervalue = buffer.value.decode("utf-8")
        print('device found: '+ buffervalue)  #for debugging with breakpoint her
        print(library_str)
        #Establishes a connection to a device
        self._nanopositionersdll.SA_CTL_Open.restypes = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_Open.argtypes = [ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_char),ctypes.POINTER(ctypes.c_char)]
        dhandle =  ctypes.c_uint32()
        connect = self._nanopositionersdll.SA_CTL_Open(dhandle, buffer, None)
        print(library_str)
        #closes connection to device
        self._nanopositionersdll.SA_CTL_Close.argtype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_Close.restype = ctypes.POINTER(ctypes.c_uint32)
        connect = self._nanopositionersdll.SA_CTL_Close(dhandle)
        print(library_str)


def main():
    nanpos = Nanopositioners()

if __name__ == "__main__":

    main()




