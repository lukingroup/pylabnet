from NKTP_DLL import *
from time import sleep

# result = registerWriteU8('COM12', 15, 0x30, 0x03, -1)
# print('Setting emission ON - Extreme:', RegisterResultTypes(result))


# result = registerWriteU8('COM12', 15, 0x30, 0x00, -1)
# print('Setting emission OFF - Extreme:', RegisterResultTypes(result))


# rdResult, FWVersionStr = registerReadAscii('COM12', 15, 0x64, 2)
# print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))
# print(rdResult)
# print(FWVersionStr)



rdResult, readValue = registerReadU16('COM12', 15, 0x37, -1)
print('readValue:', readValue, '; read result message: ', RegisterResultTypes(rdResult))




