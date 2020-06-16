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
        self._nanopositionersdll.SA_CTL_Open.argtypes = [ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_char),ctypes.POINTER(ctypes.c_char)]
        self._nanopositionersdll.SA_CTL_Close.argtype = ctypes.POINTER(ctypes.c_uint32)
        self._nanopositionersdll.SA_CTL_Close.restype = ctypes.POINTER(ctypes.c_uint32)

        #Checks that library was loaded properly
        library_string = self._nanopositionersdll.SA_CTL_GetFullVersionString()
        library_str = library_string.decode("utf-8")
        print(library_str)

        #Finds devices connected to controller
        buffer = ctypes.create_string_buffer(4096)  #the way to have a mutable buffer
        buffersize = ctypes.c_size_t(ctypes.sizeof(buffer)) #size _t gives c_ulonglong, not as in manual
        result = self._nanopositionersdll.SA_CTL_FindDevices(None, buffer,buffersize)
        buffervalue = buffer.value.decode("utf-8")
        print('Device found at: '+ buffervalue)  #for debugging with breakpoint her

        #Establishes a connection to a device
        self.dhandle =  ctypes.c_uint32()
        connect = self._nanopositionersdll.SA_CTL_Open(self.dhandle, buffer, None)
        #print('device dhanlde: ' + str(dhandle.value))
        if connect == 0:
            print('Success: device is connected')

        #Terminates connection to device
        connect = self._nanopositionersdll.SA_CTL_Close(self.dhandle)
        print('connect result: ' + str(connect))


    def move(self):

        #defines arguments and results for c functions in move function
        self._nanopositionersdll.SA_CTL_SetProperty_i32.argtypes = [ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_int8),ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_int32)]
        #self._nanopositionersdll.SA_CTL_SetProperty_i32.restype = ctypes.POINTER(ctypes.c_uint32)
        #self._nanopositionersdll.SA_CTL_Move.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_int8), ctypes.POINTER(ctypes.c_int64),ctypes.POINTER(ctypes.c_uint32)]
        #self._nanopositionersdll.SA_CTL_Stop.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint32)]

        #define movement parameters to input in c functions
        channel = ctypes.c_int8(0)
        modetype = ctypes.c_uint32(int("0x03050087",16))
        profreq = ctypes.c_uint32(int("0x0305002E",16))
        proamp = ctypes.c_uint32(int("0x03050030",16))
        stepmode = ctypes.c_int32(4)
        #stepnumber = ctyeps.uint64(1)
        freq = ctypes.c_int32(100)
        amp = ctypes.c_int32(100)

        #set mode to relative movement and define frequency and amplitude
        resultmode = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, modetype, stepmode) #define move mode SA_CTL_MOVE_MODE_STEP
        resultfreq = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, profreq, freq)
        resultamp = self._nanopositionersdll.SA_CTL_SetProperty_i32(self.dhandle, channel, proamp,  amp)

        #move command to positioner in a specific channel
        #moveresult = self._nanopositionersdll.SA_CTL_Move(self.dhandle, channel, stepnumber, 0)
        #if moveresult == 0:
        #    print('Positioner moving in channel ' + str(channel))



def main():
    nanpos = Nanopositioners()

    nanpos.move()

if __name__ == "__main__":

    main()




