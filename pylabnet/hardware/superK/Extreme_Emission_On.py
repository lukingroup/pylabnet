from NKTP_DLL import *

result = registerWriteU8('COM12', 15, 0x30, 0x03, -1)
print('Setting emission ON - Extreme:', RegisterResultTypes(result))


