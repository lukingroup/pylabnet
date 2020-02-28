import numpy as np


class PID:
    """Generic class for PID locking"""

    def __init__(self, p=0, i=0, d=0, setpoint=0, memory=20):
        """ Constructor for PID class
        
        :rtype: object
        :param p: proportional gain
        :param i: integral
        :param d: differential
        :param setpoint: setpoint for process variable
        :param memory: number of samples for integral memory
        """

        self.p = p
        self.i = i
        self.d = d
        self.memory = memory
        self.setpoint = setpoint
        self._pv = np.zeros(self.memory)
        self.cv = 0
        self.error = 0

    def set_parameters(self, p=None, i=None, d=None, setpoint=None, memory=None):
        """ Sets parameters of PID controller

        :param p: proportional gain
        :param i: integral
        :param d: differential
        :param setpoint: setpoint for process variable
        :param memory: number of samples for integral memory
        """

        if p is not None:
            self.p = p
        if i is not None:
            self.i = i
        if d is not None:
            self.d = d
        if memory is not None:
            self.memory = memory
        if setpoint is not None:
            self.setpoint = setpoint

        # Update process variable history to have appropriate length if too short
        pv_length = len(self._pv)
        if pv_length < self.memory:

            # Pad constants onto the beginning of the array
            self._pv = np.hstack((np.ones(self.memory-pv_length)*self._pv[0], self._pv))

    def set_pv(self, pv=np.zeros(10)):
        """ Sets process variable

        :param pv: process variable (measured value of process to be locked).
            This should ideally be a numpy array of recent data points
        """

        # Check the length of the input
        pv_length = len(pv)

        # If it's too short, append it onto the current pv
        if pv_length < self.memory:
            self._pv = np.append(self._pv[self.memory-pv_length:], pv)

        # Otherwise just take the last elements
        else:
            self._pv = pv[pv_length-self.memory:]

    def set_cv(self):
        """Calculates the appropriate value of the control variable"""

        # Calculate error
        error = self._pv - self.setpoint
        self.error = error[-1]

        # Calculate response
        self.cv = self.p*error[-1] + self.i*np.sum(error)/self.memory + self.d*(error[-1] - error[-2])
