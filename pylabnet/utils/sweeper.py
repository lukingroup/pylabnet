import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.igui.iplot import SingleTraceFig


class Sweep1D:

    def __init__(self, logger=None):
        """ Instantiates sweeper

        :param logger: instance of LogClient
        """

        self.log = LogHandler(logger)

        self.min = 0
        self.max = 1
        self.pts = 51
        self.x_data = np.linspace(self.min, self.max, self.pts)
        self.y_data = np.zeros(self.pts)
        self.experiment = None
        self.fixed_params = {}
        self.iplot_fwd = None

    def set_parameters(self, **kwargs):
        """ Configures all parameters

        :param kwargs: (dict) containing parameters
            :min: (float) minimum value to sweep from
            :max: (float) maximum value to sweep to
            :pts: (int) number of points to use
        """

        if 'min' in kwargs:
            self.min = kwargs['min']
        if 'max' in kwargs:
            self.max = kwargs['max']
        if 'pts' in kwargs:
            self.pts = kwargs['pts']
            self.y_data = np.zeros(self.pts)
        if 'min' in kwargs or 'max' in kwargs or 'pts' in kwargs:
            self.x_data = np.linspace(self.min, self.max, self.pts)

    def configure_experiment(
        self, experiment, experiment_params={}
    ):
        """ Sets the experimental script to a provided module

        :param experiment: (callable) method to run
        :param experiment_params: (dict) containing name and value of
            fixed parameters
        """

        self.experiment = experiment
        self.fixed_params = experiment_params

    def run_once(self, param_value):
        """ Runs the experiment once for a parameter value 

        :param_value: (float) value of parameter to use
        :return: (float) value resulting from experiment call
        """

        result = self.experiment(
            param_value, 
            **self.fixed_params
        )
        return result

    def run(self, plot=False):
        """ Runs the sweeper 
        
        :param plot: (bool) whether or not to interactively plot in notebook
        """

        if plot:
            self.iplot_fwd = SingleTraceFig(title_str='Forward Scan')
            self.iplot_fwd.show()
            self.iplot_fwd.set_data(x_ar=self.x_data)
            self.iplot_fwd.set_data(y_ar=np.array([]))

        for index, x_value in enumerate(self.x_data):
            self.y_data[index] = self.run_once(x_value)
            self.iplot_fwd.append_data(y_ar=np.array([self.y_data[index]]))
