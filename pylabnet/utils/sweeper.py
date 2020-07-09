import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.gui.igui.iplot import MultiTraceFig, HeatMapFig


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
        self.hplot_fwd = None
        self.iplot_bwd = None
        self.hplot_bwd = None
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

    def run(self):
        """ Runs the sweeper """

        sweep_points = self._generate_x_axis()
        if self.sweep_type != 'sawtooth':
            bw_sweep_points = self._generate_x_axis(backward=True)
        self._configure_plots()

        reps_done = 0
        while reps_done < self.reps or self.reps <= 0:

            self._reset_plots()

            for x_value in sweep_points:
                self._run_and_plot(x_value)
            
            if self.sweep_type != 'sawtooth':
                for x_value in bw_sweep_points:
                    self._run_and_plot(x_value, backward=True)

            reps_done += 1
            self._update_hmaps(reps_done)
            self._update_integrated(reps_done)

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

        # single-trace scans        
        self.iplot_fwd = MultiTraceFig(title_str='Forward Scan', ch_names=['Single', 'Average'])
        self.iplot_fwd.show()
        self.iplot_fwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
        self.iplot_fwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)

        # heat map
        self.hplot_fwd = HeatMapFig(title_str='Forward Scans')
        self.hplot_fwd.show()
        self.hplot_fwd.set_data(
            x_ar=np.linspace(self.min, self.max, self.pts), 
            y_ar=np.array([]), 
            z_ar=np.array([[]])
        )

        if self.sweep_type != 'sawtooth':
            self.iplot_bwd = MultiTraceFig(title_str='Backward Scan', ch_names=['Single', 'Average'])
            self.iplot_bwd.show()
            self.iplot_bwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
            self.iplot_bwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)

            # heat map
            self.hplot_bwd = HeatMapFig(title_str='Backward Scans')
            self.hplot_bwd.show()
            self.hplot_bwd.set_data(
                x_ar=np.linspace(self.max, self.min, self.pts), 
                y_ar=np.array([]), 
                z_ar=np.array([[]])
            )

    def _run_and_plot(self, x_value, backward=False):
        """ Runs the experiment for an x value and adds to plot

        :param x_value: (double) experiment parameter
        :param backward: (bool) whether or not backward or forward
        """

        y_value = self.run_once(x_value)
        if backward:
            self.iplot_bwd.append_data(x_ar=x_value, y_ar=y_value, ind=0)
        else:
            self.iplot_fwd.append_data(x_ar=x_value, y_ar=y_value, ind=0)

    def _update_hmaps(self, reps_done):
        """ Updates heat map plots 
        
        :param reps_done: (int) number of repetitions done
        """

        if reps_done == 1:
            self.hplot_fwd.set_data(
                y_ar=np.array([1]),
                z_ar=[self.iplot_fwd._y_ar]
            )
            if self.sweep_type != 'sawtooth':
                self.hplot_bwd.set_data(
                    y_ar=np.array([1]),
                    z_ar=[self.iplot_bwd._y_ar]
                )
        else:
            self.hplot_fwd.append_row(y_val=reps_done, z_ar=self.iplot_fwd._fig.data[0].y)
            if self.sweep_type != 'sawtooth':
                self.hplot_bwd.append_row(y_val=reps_done, z_ar=self.iplot_bwd._fig.data[0].y)

    def _reset_plots(self):
        """ Resets single scan traces """

        self.iplot_fwd.set_data(x_ar=np.array([]), y_ar=np.array([]))
        if self.sweep_type != 'sawtooth':
            self.iplot_bwd.set_data(x_ar=np.array([]), y_ar=np.array([]))

    def _update_integrated(self, reps_done):
        """ Updates integrated plots 
        
        :param reps_done: (int) number of repetitions completed
        """
  
        if reps_done==1:
            self.iplot_fwd.set_data(
                x_ar=np.linspace(self.min, self.max, self.pts),
                y_ar=self.iplot_fwd._fig.data[0].y,
                ind=1
            )
            if self.sweep_type != 'sawtooth':
                self.iplot_bwd.set_data(
                    x_ar=np.linspace(self.max, self.min, self.pts),
                    y_ar=self.iplot_bwd._fig.data[0].y,
                    ind=1
                )

        else:
            self.iplot_fwd.set_data(
                x_ar=np.linspace(self.min, self.max, self.pts),
                y_ar=((self.iplot_fwd._fig.data[1].y*(reps_done-1)/reps_done)
                      +self.iplot_fwd._fig.data[0].y/reps_done),
                ind=1
            )
        
            if self.sweep_type != 'sawtooth':
                self.iplot_bwd.set_data(
                    x_ar=np.linspace(self.max, self.min, self.pts),
                    y_ar=((self.iplot_bwd._fig.data[1].y*(reps_done-1)/reps_done)
                          +self.iplot_bwd._fig.data[0].y/reps_done),
                    ind=1
                )


class MultiChSweep1D(Sweep1D):
    
    def __init__(self, logger=None):
        """ Instantiates sweeper

        :param loggeR: instance of LogClient
        """

        super().__init__(logger)
