""" Module for controlling attocube open-loop nanopositioners using the ANC300 controller """


from pylabnet.network.core.service_base import ServiceBase
from pylabnet.utils.logging.logger import LogHandler
from telnetlib import Telnet
import time
import re



class ANC300:

     # compiled regular expression for finding numerical values in reply strings
    _reg_value = re.compile(r"\w+\s+=\s+(\w+)")

    def __init__(self, host, port=0, query_delay=0.05, passwd='123456', logger=None):
        """ Instantiate Nanopositioners"""


        self.log = LogHandler(logger)
        self.connection = Telnet(host, port)
        self.query_delay = query_delay
        self.lastcommand = ""

        self.read_termination = '\r\n'
        self.write_termination = self.read_termination
        time.sleep(query_delay)
        ret = self._read(check_ack=False)

        self._write(passwd, check_ack=False)
        time.sleep(self.query_delay)
        ret = self._read(check_ack=False)
        authmsg = ret.split(self.read_termination)[1]

       
        if authmsg != 'Authorization success':
            self.log.error(f"Attocube authorization failed '{authmsg}'")
        else:
            self.log.info("ANC300 successfully connected.")


    def _check_acknowledgement(self, reply, msg=""):
        """ checks the last reply of the instrument to be 'OK', otherwise a
        ValueError is raised.
        :param reply: last reply string of the instrument
        :param msg: optional message for the eventual error
        """
        if reply != 'OK':
            if msg == "":  # clear buffer
                msg = reply
                self._read()
            raise ValueError("AttocubeConsoleAdapter: Error after command "
                             f"{self.lastcommand} with message {msg}")

    def _read(self, check_ack=True):
        """ Reads a reply of the instrument which consists of two or more
        lines. The first ones are the reply to the command while the last one
        is 'OK' or 'ERROR' to indicate any problem. In case the reply is not OK
        a ValueError is raised.
        :returns: String ASCII response of the instrument.
        """
        time.sleep(self.query_delay)
        ret = self.connection.read_some().decode() + \
                self.connection.read_very_eager().decode()
                
        raw = ret.strip(self.read_termination)
        # one would want to use self.read_termination as 'sep' below, but this
        # is not possible because of a firmware bug resulting in inconsistent
        # line endings
        
        if check_ack:
            split_return = raw.rsplit(sep='\n')
            if len(split_return) == 3:
                # No argument returned
                check =  split_return[-2].strip("\r")
                ret = split_return[0].strip("\r")
            elif len(split_return) == 4:
                check =  split_return[-2].strip("\r")
                ret = split_return[1].strip("\r")

            self._check_acknowledgement(check)

        return ret

    def _extract_value(self, reply):
        """ preprocess_reply function for the Attocube console. This function
        tries to extract <value> from 'name = <value> [unit]'. If <value> can
        not be identified the original string is returned.
        :param reply: reply string
        :returns: string with only the numerical value, or the original string
        """
        r = self._reg_value.search(reply)
        if r:
            return r.groups()[0]
        else:
            return reply


    def _write(self, command, check_ack=True):
        """ Writes a command to the instrument
        :param command: command string to be sent to the instrument
        :param check_ack: boolean flag to decide if the acknowledgement is read
            back from the instrument. This should be True for set pure commands
            and False otherwise.
        """
        time.sleep(self.query_delay)
        self.lastcommand = command
        command = command + self.write_termination
        self.connection.write(command.encode())

        reply = None

        if check_ack:
            reply = self._read(check_ack=True)
            #msg =  reply.strip(self.read_termination)
            #self.check_acknowledgement(msg)
        return reply

    def _set_mode(self, channel, mode):
        self._write(f"setm {str(channel)} {str(mode)}")

    def ground(self, channel):
        self._set_mode(channel, 'gnd')
        self.log.info(f"Grounded channel {channel}.")

    def set_parameters(self, channel, mode=None, frequency=None, amplitude=None):
        """ Sets parameters for motion

        Leave parameter as None in order to leave un-changed

        :param channel: (int) index of channel from 0 to self.num_ch
        :param mode: (str) default is 'step', 
        :param freq: (int) frequency in Hz from 1 to 20000
        :param amp: (float) amplitude in volts from 0 to 100
        """
        pass


    def get_step_voltage(self, channel):
        """ Returns the cstep voltage in V

        :param channel: (int) channel index (from 1)
        """
        return self._extract_value(self._write(f"getv {str(channel)}")) 
         

    def set_step_voltage(self, channel, voltage=30):
        """ Sets the step voltage to the piezo

        :param channel: (int) channel index (from 0)
        :param voltage: (float) voltage to set from 0 to 100 V (default is 30)
        """
        
        self._write(f"setv {str(channel)} {str(voltage)}")
        self.log.info(f"Change step voltage of channel {channel} to {voltage}.")

    def get_step_frequency(self, channel):
        """ Returns the step frequency on channel

        :param channel: (int) channel index (from 1)
        """
        return self._extract_value(self._write(f"getf {str(channel)}")) 
         
    
    def set_step_frequency(self, channel, freq=1000):
        """ Sets the step voltage to the piezo

        :param channel: (int) channel index (from 0)
        :param voltage: (float) voltage to set from 0 to 100 V (default is 30)
        """
        self._write(f"setf {str(channel)} {str(freq)}")
        self.log.info(f"Change step frequency of channel {channel} to {freq}.")


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
    import time

    host = "192.168.50.208"
    port = 7230
 

    anc = ANC300(host=host, port=port)
    anc.set_step_voltage(1, 30)
    voltage = anc.get_step_voltage(2)


    anc.set_step_frequency(2, 700)
    freq = anc.get_step_frequency(2)

    print(f"Voltage {voltage}, freq {freq}")