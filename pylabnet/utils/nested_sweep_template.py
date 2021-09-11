import numpy as np


n1 = 5
n2 = 3
n3 = 2

ar1 = np.linspace(start=0, stop=n1 - 1, num=n1)
ar2 = np.linspace(start=0, stop=n2 - 1, num=n2)
ar3 = np.linspace(start=0, stop=n3 - 1, num=n3)

idx1 = 0
idx2 = 0
idx3 = 0


if idx1 < n1 and idx2 < n2 and idx3 < n3:

    stop_req = False

    while True:
        # Perform operation
        print('p1 = {} ================'.format(ar1[idx1]))

        while True:
            # Perform operation
            print('p2 = {} -------'.format(ar2[idx2]))

            while True:
                # Perform operation
                print('p3 = {}'.format(ar3[idx3]))

                if stop_req:
                    print('Loop 3 stopped')
                    break
                else:
                    idx3 += 1
                    if idx3 == n3:
                        idx3 = 0
                        break

            if stop_req:
                print('Loop 2 stopped')
                break
            else:
                idx2 += 1
                if idx2 == n2:
                    idx2 = 0
                    break

        if stop_req:
            print('Loop 1 stopped')
            break
        else:
            idx1 += 1
            if idx1 == n1:
                idx1 = 0
                break

    if stop_req:
        print('Stop hardware')


# Level template
# while True:
#     # Operation
#     # ========
#
#     # Index incrementation
#     if stop_req:
#         break
#     else:
#         idx += 1
#         if idx == n:
#             idx = 0
#             break
