import ctypes
import pyvisa
from pylabnet.utils.logging.logger import LogClient
from pylabnet.network.core.generic_server import GenericServer
#from pylabnet.network.client_server.pol_paddles import Client
from pylabnet.hardware.power_meter.thorlabs_pm320e import Driver
from pylabnet.hardware.polarization.polarization_control import Driver as MPC320 , paddle1, paddle2, paddle3
import time
import numpy as np
import matplotlib.pyplot as plt


gpib_addres = 'USB0::0x1313::0x8022::M00579698::INSTR'
# device = b'38154354'  #device serial number = b'38154354' #dummy pol setup
device_num = 1 # pick number of device in list. Current pol paddles are device_num = 1 in list.

# Instantiate
logger = LogClient(
    host='139.180.129.96',
    port=24949,
    module_tag='Polarization Optimizer'
)
power_meter = Driver(
    gpib_address=gpib_addres, 
    logger=logger
)

pol_paddle = MPC320(
    device_num=device_num, 
    logger=logger) 

power_meter.set_range(2,'R100NW')

# Output of pol. paddle is connected to output 2 of powermeter
channel = 2
init_power = power_meter.get_power(channel)

print(f"Initial power is {init_power} W.")
paddles = [paddle1, paddle3, paddle2]
#pol_paddle.open()

velocity = 100 #percentage from 0 to 100
pol_paddle.set_velocity(velocity)

for paddle in paddles:
    home = pol_paddle.home(1)
    move = pol_paddle.move(1, 85)

Posf = pol_paddle.get_angle(paddle2)

#wrap optimizer as function define function
#get initial central pos, range of angles, number of step (resolution) and find the angle of maximum power for these inputs)
#def optimize(angle_center_1,angle_center_2,angle_center_3 deviate, stepnum)
count = 0
itercount = 0
ang = [] 
angle = []
power = []
pos = []
iterationnum = 40
stepnum = 20 #number of step angles within range Cannot go below 2 in full range to have enough time for paddle to repond (defined in move function in driver)
ang_paddles = []
power_paddles = []

for paddle in paddles:
    deviate = 170 #range of angle to scan
    stepsize = deviate/stepnum
    move_in = pol_paddle.move_rel(paddle, -deviate/2)
    while itercount < iterationnum:
        if itercount >= 1:
            move = pol_paddle.move(paddle, ang[itercount-1]-deviate/2)
        while count < stepnum:
            mover = pol_paddle.move_rel(paddle, stepsize)
            PosF = pol_paddle.get_angle(paddle)
            print(f"itercount = {itercount} count = {count}")
            print(f"Position after move relative is {PosF}") 
            current_power = power_meter.get_power(channel)
            print(f"Current power is {current_power} W.")
            power.extend([current_power])
            angle.extend([PosF])
            #plt.title(f"paddle # {paddle} , iteration # {itercount}.")
            #plt.plot(angle[count], power[count], "or")
            #plt.show()
            count += 1
        #plt.title(f"paddle # {paddle.value} , iteration # {itercount}.")
        #plt.plot(angle, power, "or")
        maxindex = np.argmax(power)
        ang.extend([angle[maxindex]]) 
        if itercount >= 1:
            if abs(ang[itercount] - ang[itercount-1]) < 0.05:
                print(f"converged to max power.")
                move = pol_paddle.move(paddle, angle[maxindex])
                count = 0
                itercount = 0
                power = []
                angle = []
                break

        deviate = deviate/2
        stepsize = deviate/stepnum
        itercount += 1
        count = 0

    ang_paddles.extend(ang)
    power_paddles.extend(power)
    ang = []
    itercount = 0
    
PosF1 = pol_paddle.get_angle(paddles[0])
print(f"paddle = {paddles[0].value} final_angle = {PosF1}")
PosF2 = pol_paddle.get_angle(paddles[1])
print(f"paddle = {paddles[1].value} final_angle = {PosF2}")
PosF3 = pol_paddle.get_angle(paddles[2])
print(f"paddle = {paddles[2].value} final_angle = {PosF3}")

pol_paddle.close()




