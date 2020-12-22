import pyvisa
from pylabnet.utils.logging.logger import LogClient
from pylabnet.network.core.generic_server import GenericServer
from pylabnet.hardware.power_meter.thorlabs_pm320e import Driver
from pylabnet.hardware.polarization.polarization_control import MPC320, paddle1, paddle2
import time
import numpy as np

gpib_addres = 'USB0::0x1313::0x8022::M00579698::INSTR'

# Instantiate
logger = LogClient(
    host='139.180.129.96',
    port=13832,
    module_tag='Polarization Optimizer'
)
power_meter = Driver(
    gpib_address=gpib_addres, 
    logger=logger
)

power_meter.set_range(2, 'R100UW')

pol_paddle = MPC320()

# Output of pol. paddle is connected to output 2 of powermeter
channel = 2
init_power = power_meter.get_power(channel)

print(f"Initial power is {init_power} W.")

paddle = paddle1
#device = '38154354' #dummy setup
device = pol_paddle.device_info.serialNo
stepsize = 10 #degrees
step = 10
stepnum = 20
pos = 10

pol_paddle.open(device)

#home = pol_paddle.home(device, paddle)
#Posf = pol_paddle.get_angle(device, paddle)
#movement_rel = pol_paddle.move_rel(device, paddle, step)
#Posf = pol_paddle.get_angle(device, paddle)

#optimize pol for max power
home = pol_paddle.home(device, paddle)
movement = pol_paddle.move(device, paddle, pos)
ang = []
angle = []
power = []
pos = []
deviate = 150
stepnum = 50
stepsize = deviate/stepnum
iterationnum = 20
count = 0
itercount = 0

while itercount < iterationnum:
    if itercount >= 1:
        move = pol_paddle.move(device, paddle, ang[itercount-1]-deviate/2)
        time.sleep(10)
    while count < stepnum:
        mover = pol_paddle.move_rel(device, paddle, stepsize)
        time.sleep(5)
        count += 1
        PosF = pol_paddle.get_angle(device, paddle)
        print(f"itercount = {itercount} count = {count}")
        print(f"Position after move relative is {PosF}") 
        current_power = power_meter.get_power(channel)
        print(f"Current power is {current_power} W.")
        power.extend([current_power])
        angle.extend([PosF])
    
    maxindex = np.argmax(power)
    ang.extend([angle[maxindex]]) 
    if itercount >= 1:
        if abs(ang[itercount] - ang[itercount-1]) < 0.5:
            print(f"converged to max power.")
            break
    deviate = deviate/2
    stepsize = deviate/stepnum
    itercount += 1
    count = 0

pol_paddle.close(device)




