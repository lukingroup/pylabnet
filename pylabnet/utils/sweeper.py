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
        self.experiment = None
        self.fixed_params = {}
        self.iplot_fwd = None
        self.iplot_bwd = None
        self.sweep_type = 'triangle'
        self.reps = 0

    def set_parameters(self, **kwargs):
        """ Configures all parameters

        :param kwargs: (dict) containing parameters
            :min: (float) minimum value to sweep from
            :max: (float) maximum value to sweep to
            :pts: (int) number of points to use
            :reps: (int) number of experiment repetitions
            :sweep_type: (str) 'triangle' or 'sawtooth' supported
        """

        if 'min' in kwargs:
            self.min = kwargs['min']
        if 'max' in kwargs:
            self.max = kwargs['max']
        if 'pts' in kwargs:
            self.pts = kwargs['pts']
        if 'sweep_type' in kwargs:
            sweep_str = kwargs['sweep_type']
            if sweep_str == 'sawtooth':
                self.sweep_type = sweep_str
            else:
                self.sweep_type = 'triangle'
        if 'reps' in kwargs:
            self.reps = kwargs['reps']

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

        sweep_points = self._generate_x_axis()
        if self.sweep_type != 'sawtooth':
            bw_sweep_points = self._generate_x_axis(backward=True)
        self._configure_plots()

        reps_done = 0
        while reps_done < self.reps or self.reps <= 0:

            for x_value in sweep_points:
                self._run_and_plot(x_value)
            
            if self.sweep_type != 'sawtooth':
                for x_value in bw_sweep_points:
                    self._run_and_plot(x_value, backward=True)

            reps_done += 1

    def _generate_x_axis(self, backward=False):
        """ Generates an x-axis based on the type of sweep 
        
        Currently only implements triangle
        :param backward: (bool) whether or not it is a backward scan
        :return: (np.array) containing points to scan over
        """

        if backward:
            return np.linspace(self.max, self.min, self.pts)
        else:
            return np.linspace(self.min, self.max, self.pts)

    def _configure_plots(self):
        """ Configures all plots """

        self.iplot_fwd = SingleTraceFig(title_str='Forward Scan')
        self.iplot_fwd.show()
        self.iplot_fwd.set_data(x_ar=np.array([]))
        self.iplot_fwd.set_data(y_ar=np.array([]))

        if self.sweep_type != 'sawtooth':
            self.iplot_bwd = SingleTraceFig(title_str='Backward Scan')
            self.iplot_bwd.show()
            self.iplot_bwd.set_data(x_ar=np.array([]))
            self.iplot_bwd.set_data(y_ar=np.array([]))


    def _run_and_plot(self, x_value, backward=False):
        """ Runs the experiment for an x value and adds to plot

        :param x_value: (double) experiment parameter
        :param backward: (bool) whether or not backward or forward
        """

        y_value = self.run_once(x_value)
        if backward:
            self.iplot_bwd.append_data(x_ar=x_value)
            self.iplot_bwd.append_data(y_ar=y_value)
        else:
            self.iplot_fwd.append_data(x_ar=x_value)
            self.iplot_fwd.append_data(y_ar=y_value)
