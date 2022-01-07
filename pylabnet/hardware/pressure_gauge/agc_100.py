import time
import serial
import io

from pylabnet.utils.logging.logger import LogHandler

class AGC_100:

    def __init__(self, port, logger=None):
        """Instantiates serial connection to pressure gauge
        """
        # Instantiate log
        self.log = LogHandler(logger=logger)

        ser = serial.Serial(
            port=port,
            baudrate=9600,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

        self.sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

        # Log initial pressure. 
        init_pressure = self.get_pressure()
        self.log.info(f"Successfully reading {init_pressure} mBar.")

    def get_pressure(self):
        '''Returns pressure in mBar'''
        raw_data = self.sio.readline()
        pressure = float(raw_data.split(",")[1].replace(" mbar", ""))
        return pressure
