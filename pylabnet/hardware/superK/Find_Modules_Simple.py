from NKTP_DLL import *

print('Find modules on all existing and accessible ports - Might take a few seconds to complete.....')
if (getLegacyBusScanning()):
    print('Scanning following ports in legacy mode:', getAllPorts())
else:
    print('Scanning following ports in normal mode:', getAllPorts())

# Use the openPorts function with Auto & Live settings. This will scan and detect modules
# on all ports returned by the getAllPorts function.
# Please note that a port being in use by another application, will show up in this list but will
# not show any devices due to this port being inaccessible.
print(openPorts(getAllPorts(), 1, 1))

# All ports returned by the getOpenPorts function has modules (ports with no modules will automatically be closed)
print('Following ports has modules:', getOpenPorts())

# Traverse the getOpenPorts list and retrieve found modules via the deviceGetAllTypes function
portlist = getOpenPorts().split(',')
for portName in portlist:
    result, devList = deviceGetAllTypes(portName)
    for devId in range(0, len(devList)):
        if (devList[devId] != 0):
            print('Comport:',portName,'Device type:',"0x%0.2X" % devList[devId],'at address:',devId)

# Close all ports
closeResult = closePorts('')
print('Close result: ', PortResultTypes(closeResult))

