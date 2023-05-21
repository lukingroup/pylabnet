from NKTP_DLL import *
from time import sleep


# Open the COM port
# Not nessesary, but would speed up the communication, since the functions does
# not have to open and close the port on each call
openResult = openPorts('COM43', 0, 0)
print('Opening the comport:', PortResultTypes(openResult))

# Example - Reading of the Firmware Revision register 0x64(regId) in BASIK (K1x2) at address 8 (devId)
# index = 2, because the str starts at byte index 2
rdResult, FWVersionStr = registerReadAscii('COM43', 8, 0x64, 2)
print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

# Example - Turn on emission on BASIK (K1x2) by setting register 0x30 = 1
# See SDK Instruction Manual page 41
wrResult = registerWriteU8('COM43', 8, 0x30, 1, -1) 
print('Turn on emission:', RegisterResultTypes(rdResult))

print('sleeping for 4 seconds')
sleep(4.0)

# Example get serial number str
rdResult, serial = deviceGetModuleSerialNumberStr('COM43', 8)
print('Serial:', serial, DeviceResultTypes(rdResult))
      
# Example - Turn off emission on BASIK (K1x2) by setting register 0x30 = 0
# See SDK Instruction Manual page 41
wrResult = registerWriteU8('COM43', 8, 0x30, 0, -1) 
print('Turn off emission:', RegisterResultTypes(wrResult))

# Close the Internet port
closeResult = closePorts('COM43')
print('Close the comport:', PortResultTypes(closeResult))

