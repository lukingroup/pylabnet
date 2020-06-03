import ctypes

class Nanopositioners():

    def __init__(self):
        """ Instantiate Nanopositiners"""

        #Loads Nanopositioners DLL and
        self._nanopositionersdll = ctypes.windll.LoadLibrary('SmarActCTL.dll')

        #Defines arguments and results for c function
        self._nanopositionersdll.SA_CTL_GetFullVersionString.restype = ctypes.c_char_p
        self._nanopositionersdll.SA_CTL_FindDevices.restype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_FindDevices.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_ulonglong)]
        self._nanopositionersdll.SA_CTL_Open.restypes = ctypes.POINTER(ctypes.c_uint32)
        #self._nanopositionersdll.SA_CTL_Open.argtypes = [ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_char),ctypes.POINTER(ctypes.c_char)]

        #Checks that library was loaded properly
        library_string = self._nanopositionersdll.SA_CTL_GetFullVersionString()
        library_str = library_string.decode("utf-8")
        print(library_str)

        #Finds devices connected to controller
        buffer = ctypes.create_string_buffer(4096)  #the way to have a mutable buffer
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer)) #size _t gives c_ulonglong, not as in manual
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, buffer,buffersize)
        buffervalue = buffer.value.decode("utf-8")
        print('device found: '+ buffervalue)  #for debugging with breakpoint her

        #Establishes a connection to a device
        dhandle =  ctypes.c_uint32()
        connect = self._nanopositionersdll.SA_CTL_Open(ctypes.byref(dhandle), ctypes.byref(buffer), None)
        print(str(dhandle.value))

        #Terminates connection to device
        self._nanopositionersdll.SA_CTL_Close.argtype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_Close.restype = ctypes.POINTER(ctypes.c_uint32)
        connect = self._nanopositionersdll.SA_CTL_Close(dhandle)
        print(str(connect))




def main():
    nanpos = Nanopositioners()

if __name__ == "__main__":

    main()




