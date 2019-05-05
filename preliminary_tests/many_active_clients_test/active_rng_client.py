import sys
sys.path.append(r'C:\Users\Lukin SiV\pylabnet\preliminary_tests')
from rng import RNGClient
import sys
import time
import numpy as np


if __name__ == '__main__':

    client_number = int(sys.argv[1])
    ar_size = int(sys.argv[2])
    print('Client number is {}. Array size is {}'.format(client_number, ar_size))

    remote_rng = RNGClient(host='localhost', port=18891)
    print('Connected to remote RNG')

    ret_code = remote_rng.build_test_array(client_number=client_number, size=ar_size)
    if ret_code == 0:
        print('Successfully constructed individual array ')
    else:
        print('Construction of array by remote RNG failed')

    start_t = time.time()
    i = 0
    while True:
        i += 1
        ret_array = remote_rng.ret_test_array(client_number=client_number)

        if i%1000 == 0:
            call_t = (time.time() - start_t) / 1000
            point_t = call_t / ar_size

            ar_mean = np.sum(ret_array) / ar_size

            print('call_t: {:8.2f} ms'.format(call_t*1e3))
            print('point_t: {:7.2f} us'.format(point_t*1e6))
            print('ar_mean: {:7.2f}'.format(ar_mean))

            ret_code = remote_rng.build_test_array(client_number=client_number, size=ar_size)
            start_t = time.time()
            i = 0



