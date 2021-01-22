# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import numpy as np
from pylabnet.utils.logging.logger import LogClient
from pylabnet.network.client_server.thorlabs_mpc320 import Client as pol_paddle_Client
from pylabnet.network.client_server.thorlabs_pm320e import Client as power_meter_Client
import matplotlib.pyplot as plt


# %%
pol_paddle_client = pol_paddle_Client(
    host='139.180.129.96',
    port=25806,
)


# %%
power_meter_client = power_meter_Client(
    host='139.180.129.96',
    port=12109,
)


# %%
#settings for polarization paddle and power meter 
channel = 2
p_range = 'R1NW'
paddles = [0,1,2]
velocity = 100 #percentage from 0 to 100
pol_paddle_client.set_velocity(velocity) 
power_meter_client.set_range(channel, p_range)


# %%
#set parameters for optimization code
count = 0
iter_count = 0  #initialized to zero and gro as step in angles as taken in an single iteration
ang = [] 
angle = []
power = []
pos = []
iteration_num = 40 #number of iterations we ableto check conversion
step_num = 60 #number of step angles within range Cannot go below 2 in full range to have enough 
converge_parameter =  0.001 # resoution in angle to define convergance 
#time for paddle to repond (defined in move function in driver)
ang_paddles = []
power_paddles = []
sleep_time = 1 #defines time (in sec) that we allow paddle to move 170 degrees


# %%
#for an initial scan of all angles
for paddle in paddles:
    home = pol_paddle_client.move(paddle, 100, sleep_time)


# %%
import matplotlib.pyplot as plt


# %%
for paddle in paddles:
    deviate = 170 #range of angle to scan
    step_size = deviate/step_num
    move_in = pol_paddle_client.move_rel(paddle, -deviate/2, sleep_time)
    while iter_count < iteration_num:
        if iter_count >= 1:
            move = pol_paddle_client.move(paddle, ang[iter_count-1]-deviate/2, sleep_time)
        while count < step_num:
            mover = pol_paddle_client.move_rel(paddle, step_size, sleep_time)
            PosF = pol_paddle_client.get_angle(paddle)
            current_power = power_meter_client.get_power(channel)
            power.extend([current_power])
            angle.extend([PosF])
            count += 1
        plt.figure((paddle+1)*iteration_num)
        plt.title(f"paddle # {paddle} , iteration # {iter_count}.")
        plt.plot(angle, power, "or")
        max_index = np.argmax(power)
        ang.extend([angle[max_index]]) 
        if iter_count >= 1:
            if abs(ang[iter_count] - ang[iter_count-1]) < converge_parameter:
                print(f"converged to max power.")
                move = pol_paddle_client.move(paddle, angle[max_index], sleep_time)
                count = 0
                iter_count = 0
                power = []
                angle = []
                break

        deviate = deviate/2
        step_size = deviate/step_num
        iter_count += 1
        count = 0

    ang_paddles.extend(ang)
    power_paddles.extend(power)
    ang = []
    iter_count = 0


# %%
PosF1 = pol_paddle_client.get_angle(paddles[0])
print(f"paddle = {paddles[0]} final_angle = {PosF1}")
PosF2 = pol_paddle_client.get_angle(paddles[1])
print(f"paddle = {paddles[1]} final_angle = {PosF2}")
PosF3 = pol_paddle_client.get_angle(paddles[2])
print(f"paddle = {paddles[2]} final_angle = {PosF3}")


# %%
#closes connection to device
pol_paddle_client.close()


