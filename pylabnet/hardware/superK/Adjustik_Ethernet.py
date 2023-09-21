from NKTP_DLL import *
from time import sleep

# Create the Internet port
addResult = pointToPointPortAdd('ADJUSTIK_Eth_Port1', pointToPointPortData('192.168.250.77', 10001, '192.168.250.30', 10001, 1, 100))
print('Creating ethernet port', P2PPortResultTypes(addResult))

getResult, portdata = pointToPointPortGet('ADJUSTIK_Eth_Port1')
print('Getting ethernet port', portdata, P2PPortResultTypes(getResult))

# Open the Internet port
# Not nessesary, but would speed up the communication, since the functions does
# not have to open and close the port on each call
openResult = openPorts('ADJUSTIK_Eth_Port1', 0, 0)
print('Opening the Ethernet port:', PortResultTypes(openResult))

# Example - Reading of the Firmware Revision register 0x64(regId) in ADJUSTIK at address 128(devId)
# index = 2, because the str starts at byte index 2
rdResult, FWVersionStr = registerReadAscii('ADJUSTIK_Eth_Port1', 128, 0x64, 2)
print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

# Example - Turn on emission on ADJUSTIK by setting register 0x30 = 1
# See SDK Instruction Manual page 34
wrResult = registerWriteU8('ADJUSTIK_Eth_Port1', 128, 0x30, 1, -1) 
print('Turn on emission:', RegisterResultTypes(rdResult))

print('sleeping for 4 seconds')
sleep(4.0)

# Example - Turn off emission on ADJUSTIK by setting register 0x30 = 0
# See SDK Instruction Manual page 34
wrResult = registerWriteU8('ADJUSTIK_Eth_Port1', 128, 0x30, 0, -1) 
print('Turn off emission:', RegisterResultTypes(rdResult))

# Close the Internet port
closeResult = closePorts('ADJUSTIK_Eth_Port1')
print('Close the Ethernet port:', PortResultTypes(closeResult))

