""" Module for controlling attocube open-loop nanopositioners using the ANC300 controller """


from pylabnet.network.core.service_base import ServiceBase
from pylabnet.utils.logging.logger import LogHandler


class ANC300:


    def __init__(self, logger=None):
        """ Instantiate Nanopositioners"""

    
    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None, dc_vel=None):
        """ Sets parameters for motion

        Leave parameter as None in order to leave un-changed

        :param channel: (int) index of channel from 0 to self.num_ch
        :param mode: (str) default is 'step', can use 'dc', 'dc_rel' to set abs or rel DC voltage
        :param freq: (int) frequency in Hz from 1 to 20000
        :param amp: (float) amplitude in volts from 0 to 100
        :param dc_vel: (float) velocity for DC steps in volts/sec
        """
        pass

    def get_voltage(self, channel):
        """ Returns the current DC voltage on a piezo

        :param channel: (int) channel index (from 0)
        """
        pass

    def set_voltage(self, channel, voltage=50):
        """ Sets an absolute voltage to the piezo

        :param channel: (int) channel index (from 0)
        :param voltage: (float) voltage to set from 0 to 100 V (default is 50)
        """
        pass

    def n_steps(self, channel, n=1):
        """ Takes n steps

        :param channel: (int) channel index (from 0)
        :param n: (int) number of steps to take, negative is in opposite direction
        """
        pass


    def move(self, channel, backward=False):
        """ Takes the maximum number of steps (quasi continuous)

        :param channel: (int) channel index (from 0)
        :param backward: (bool) whether or not to step in backwards direction (default False)
        """
        pass
            

    def stop(self, channel):
        """ Terminates any ongoing movement

        :param channel: (int) channel index (from 0)
        """
        pass

    def is_moving(self, channel):
        """ Returns whether or not the positioner is moving

        :param channel: (int) channel index (from 0)

        :return: (bool) true if moving
        """


if __name__ == "__main__":
    from telnetlib import Telnet
    host = "192.168.50.208"
    port = 7230

    connection=Telnet(host, port)