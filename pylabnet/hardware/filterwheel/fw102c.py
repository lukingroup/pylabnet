# fw102c.py
#
# Thorlabs FW102C - Six-Position Motorized Filter Wheel - Python interface

# Gilles Simond <gilles.simond@unige.ch>

# who       when        what
# --------  ----------  -------------------------------------------------
# gsimond   20140922    modified from Adrien.Deline version
#

import io,re,sys
from serial import Serial, SerialException

NUM_READLINES = 8

class FW102C(object):
    """
       Class to control the ThorLabs FW102C filter wheel

          fwl = Thorlabs.FW102C(port='COM5')
          fwl.help()
          fwl.command('pos=5')
          fwl.query('pos?')
          fwl.close()

       The following table describes all of the available commands and queries:
        *idn?     Get ID: Returns the model number and firmware version
        pos=n     Moves the wheel to filter position n
        pos?      Get current Position
        pcount=n  Set Position Count: Sets the wheel type where n is 6 or 12
        pcount?   Get Position Count: Returns the wheel type
        trig=0    Sets the external trigger to the input mode
        trig=1    Sets the external trigger to the output mode
        trig?     Get current Trigger Mode
        speed=0   Sets the move profile to slow speed
        speed=1   Sets the move profile to high speed
        speed?    Returns the move profile mode
        sensors=0 Sensors turn off when wheel is idle to eliminate stray light
        sensors=1 Sensors remain active
        sensors?  Get current Sensor Mode
        baud=0    Sets the baud rate to 9600
        baud=1    Sets the baud rate to 115200
        baud?     Returns the baud rate where 0 = 9600 and 1 = 115200
        save      This will save all the settings as default on power up

    """
    isOpen   = False

    def __init__(self, port, logger):

        self.log = logger

        try:
            self._fw = Serial(port=port, baudrate=115200,
                                  bytesize=8, parity='N', stopbits=1,
                                  timeout=1, xonxoff=0, rtscts=0)
        except  SerialException as ex:
            self.log.error('Port {0} is unavailable: {1}'.format(port, ex))
            return
        except  OSError as ex:
            self.log.error('Port {0} is unavailable: {1}'.format(port, ex))
            return
        self._sio = io.TextIOWrapper(io.BufferedRWPair(self._fw, self._fw, 1),
                       newline=None, encoding='ascii')

        self._sio.flush()
        self.isOpen  = True
    # end def __init__

    def help(self):
        print(self.__doc__)
    # end def help

    def close(self):
        if not self.isOpen:
            print("Close error: Device not open")
            return "ERROR"
        #end if

        self._fw.close()
        self.isOpen = False
        return "OK"
    # end def close

    def query(self, cmdstr):
        """
           Send query, get and return answer
        """
        if not self.isOpen:
            self.log.error("Query error: Device not open")
            return "DEVICE NOT OPEN"
        #end if

        ans = 'ERROR'
        self._sio.flush()
        res = self._sio.write(str(cmdstr+'\r'))
        if res:
            ans = self._sio.readlines(NUM_READLINES)[1][:-1]
        #print 'queryans=',repr(ans)
        return ans
    # end def query

    def command(self, cmdstr):
        """
           Send command, check for error, send query to check and return answer
           If no error, answer value should be equal to command argument value
        """
        if not self.isOpen:
            self.log.error("Command error: Device not open")
            return "DEVICE NOT OPEN"

        self._sio.flush()
        res = self._sio.write(str(cmdstr+'\r'))



