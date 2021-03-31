""" Module for sweep-based experiments

Currently only supported in notebook format. Example usage:
>> exp = Sweep1D(logger=log_client)
>> exp.set_parameters(min=5, max=10, pts=51)
>> def my_experiment(**kwargs):
        client1.set_some_parameter(kwargs['param1'])
        return client2.get_some_values()
>> exp.configure_experiment(my_experiment, experiment_params=param_dict)
>> exp.set_reps(10)
>> exp.run(plot=True, autosave=True)

Note that some client-server functionality for termination is implemented,
see pylabnet.network.client_server.sweeper
"""

import numpy as np

from pylabnet.utils.logging.logger import LogHandler
from pylabnet.utils.helper_methods import generic_save, plotly_figure_save
from pylabnet.gui.igui.iplot import MultiTraceFig, HeatMapFig


class Sweep1D:

    def __init__(self, logger=None, sweep_type='triangle'):
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
        self.sweep_type = sweep_type
        self.reps = 0
        self.stop_flag = False
        self.stop_end_flag = False
        self.x_label = None
        self.y_label = None
        self.autosave = False

        # Setup stylesheet.
        #self.gui.apply_stylesheet()


    def set_parameters(self, **kwargs):
        """ Configures all parameters

        :param kwargs: (dict) containing parameters
            :min: (float) minimum value to sweep from
            :max: (float) maximum value to sweep to
            :pts: (int) number of points to use
            :reps: (int) number of experiment repetitions
            :sweep_type: (str) 'triangle' or 'sawtooth' supported
            :x_label: (str) Label of x axis
            :y_label: (str) label of y axis
        """

        if 'min' in kwargs:
            self.min = kwargs['min']
        if 'max' in kwargs:
            self.max = kwargs['max']
        if 'pts' in kwargs:
            self.pts = kwargs['pts']
        if 'sweep_type' in kwargs:
            sweep_str = kwargs['sweep_type']
            if sweep_str not in ['sawtooth',  'triangle']:
                self.log.error(
                    'Sweep type must be either "sawtooth" or "triangle".'
                )
            self.sweep_type = sweep_str
        if 'reps' in kwargs:
            self.reps = kwargs['reps']
        if 'x_label' in kwargs:
            self.x_label = kwargs['x_label']
        if 'y_label' in kwargs:
            self.y_label = kwargs['y_label']

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

    def run(self, plot=False, autosave=None, filename=None, directory=None, date_dir=True):
        """ Runs the sweeper

        :param plot: (bool) whether or not to display the plotly plot
        :param autosave: (bool) whether or not to autosave
        :param filename: (str) name of file identifier
        :param directory: (str) filepath to save to
        :param date_dir: (bool) whether or not to store in date-specific sub-directory
        """

        if autosave is not None:
            self.autosave = autosave

        sweep_points = self._generate_x_axis()
        if self.sweep_type != 'sawtooth':
            bw_sweep_points = self._generate_x_axis(backward=True)
        self._configure_plots(plot)

        reps_done = 0
        self.stop_flag = False
        while (reps_done < self.reps or self.reps <= 0 and not self.stop_flag):

            self._reset_plots()

            for x_value in sweep_points:
                if self.stop_flag:
                    break
                self._run_and_plot(x_value)

            if self.sweep_type != 'sawtooth':
                for x_value in bw_sweep_points:
                    if self.stop_flag:
                        break
                    self._run_and_plot(x_value, backward=True)

            if self.stop_flag:
                break
            reps_done += 1
            self._update_hmaps(reps_done)
            self._update_integrated(reps_done)

            # Autosave at every iteration
            if self.autosave:
                self.save(filename, directory, date_dir)

            # Print progress
            print(f'Finished {reps_done} out of {self.reps} sweeps.')

    def stop(self):
        """ Terminates the sweeper immediately """

        self.stop_flag = True

    def set_reps(self, reps=1):
        """ Sets the repetitions to be done

        :param reps: (int) number of refs
            default = 1, can be used to terminate at end of current rep
        """
        self.reps = reps

    def save(self, filename=None, directory=None, date_dir=True):
        """ Saves the dataset

        :param filename: (str) name of file identifier
        :param directory: (str) filepath to save to
        :param date_dir: (bool) whether or not to store in date-specific sub-directory
        """

        if filename is None:
            filename = 'sweeper_data'

        # Save heatmap
        generic_save(
            data=self.hplot_fwd._fig.data[0].z,
            filename=f'{filename}_fwd_scans',
            directory=directory,
            date_dir=date_dir
        )

        # Save heatmap png
        # plotly_figure_save(
        #     self.hplot_fwd._fig,
        #     filename=f'{filename}_fwd_scans',
        #     directory=directory,
        #     date_dir=date_dir
        # )

        # Save average
        generic_save(
            data = np.array(
                    [self.iplot_fwd._fig.data[1].x,
                    self.iplot_fwd._fig.data[1].y]
            ),
            filename=f'{filename}_fwd_avg',
            directory=directory,
            date_dir=date_dir
        )

        if self.sweep_type != 'sawtooth':

            # Save heatmap
            generic_save(
                data=self.hplot_bwd._fig.data[0].z,
                filename=f'{filename}_bwd_scans',
                directory=directory,
                date_dir=date_dir
            )
            # Save average
            generic_save(
                data = np.array(
                        [self.iplot_fwd._fig.data[1].x,
                        self.iplot_fwd._fig.data[1].y]
                ),
                filename=f'{filename}_bwd_avg',
                directory=directory,
                date_dir=date_dir
            )

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

    def _configure_plots(self, plot):
        """ Configures all plots

        :param plot: (bool) whether or not to display the plotly plot
        """

        # single-trace scans
        self.iplot_fwd = MultiTraceFig(title_str='Forward Scan', ch_names=['Single', 'Average'])
        self.iplot_fwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
        self.iplot_fwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)
        self.iplot_fwd.set_lbls(x_str=self.x_label, y_str=self.y_label)

        # heat map
        self.hplot_fwd = HeatMapFig(title_str='Forward Scans')
        self.hplot_fwd.set_data(
            x_ar=np.linspace(self.min, self.max, self.pts),
            y_ar=np.array([]),
            z_ar=np.array([[]])
        )
        self.hplot_fwd.set_lbls(
            x_str=self.x_label,
            y_str='Repetition number',
            z_str=self.y_label
        )

        # Show plots if enabled
        if plot:
            self.iplot_fwd.show()
            self.hplot_fwd.show()

        if self.sweep_type != 'sawtooth':
            self.iplot_bwd = MultiTraceFig(title_str='Backward Scan', ch_names=['Single', 'Average'])
            self.iplot_bwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
            self.iplot_bwd.set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)
            self.iplot_bwd.set_lbls(x_str=self.x_label, y_str=self.y_label)

            # heat map
            self.hplot_bwd = HeatMapFig(title_str='Backward Scans')
            self.hplot_bwd.set_data(
                x_ar=np.linspace(self.max, self.min, self.pts),
                y_ar=np.array([]),
                z_ar=np.array([[]])
            )
            self.hplot_bwd.set_lbls(
                x_str=self.x_label,
                y_str='Repetition number',
                z_str=self.y_label
            )

            # Show plots if enabled
            self.iplot_bwd.show()
            self.hplot_bwd.show()


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

    def __init__(self, logger=None, channels=None, sweep_type='triangle'):
        """ Instantiates sweeper

        :param logger: instance of LogClient
        :param channels: (list) list of channel names
        """

        super().__init__(logger, sweep_type=sweep_type)
        self.channels = channels

    def save(self, filename=None, directory=None, date_dir=False):
        """ Saves the dataset

        :param filename: (str) name of file identifier
        :param directory: (str) filepath to save to
        :param date_dir: (bool) whether or not to store in date-specific sub-directory
        """

        if filename is None:
            filename = 'sweeper_data'

        for channel in self.channels:

            filename = f'{filename}_{channel}'

            # Save heatmap
            generic_save(
                data=self.hplot_fwd._fig.data[0],
                filename=f'{filename}_fwd_scans',
                directory=directory,
                date_dir=date_dir
            )
            # Save average
            generic_save(
                data=self.iplot_fwd._fig.data[1],
                filename=f'{filename}_fwd_avg',
                directory=directory,
                date_dir=date_dir
            )

            if self.sweep_type != 'sawtooth':

                # Save heatmap
                generic_save(
                    data=self.hplot_bwd._fig.data[0],
                    filename=f'{filename}_bwd_scans',
                    directory=directory,
                    date_dir=date_dir
                )
                # Save average
                generic_save(
                    data=self.iplot_bwd._fig.data[1],
                    filename=f'{filename}_bwd_avg',
                    directory=directory,
                    date_dir=date_dir
                )

    def _configure_plots(self, plot):
        """ Configures all plots

        :param plot: (bool) whether or not to display the plotly plot
        """

        # Configure channel names
        if self.channels is None:
            self.channels = ['']

        # single-trace scans
        self.iplot_fwd = []
        self.hplot_fwd = []
        if self.sweep_type != 'sawtooth':
            self.iplot_bwd = []
            self.hplot_bwd = []
        for index, channel in enumerate(self.channels):
            self.iplot_fwd.append(MultiTraceFig(title_str='Forward Scan', ch_names=[
                f'{channel} Single', f'{channel} Average'
            ]))
            self.iplot_fwd[index].set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
            self.iplot_fwd[index].set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)

            # heat map
            self.hplot_fwd.append(HeatMapFig(title_str='Forward Scans'))
            self.hplot_fwd[index].set_data(
                x_ar=np.linspace(self.min, self.max, self.pts),
                y_ar=np.array([]),
                z_ar=np.array([[]])
            )

            # Show plots if enabled
            if plot:
                self.iplot_fwd[index].show()
                self.hplot_fwd[index].show()

            if self.sweep_type != 'sawtooth':
                self.iplot_bwd.append(MultiTraceFig(
                    title_str='Backward Scan',
                    ch_names=[f'{channel} Single', f'{channel} Average']
                ))
                self.iplot_bwd[index].set_data(x_ar=np.array([]), y_ar=np.array([]), ind=0)
                self.iplot_bwd[index].set_data(x_ar=np.array([]), y_ar=np.array([]), ind=1)

                # heat map
                self.hplot_bwd.append(HeatMapFig(title_str='Backward Scans'))
                self.hplot_bwd[index].set_data(
                    x_ar=np.linspace(self.max, self.min, self.pts),
                    y_ar=np.array([]),
                    z_ar=np.array([[]])
                )

                # Show plots if enabled
                if plot:
                    self.iplot_bwd[index].show()
                    self.hplot_bwd[index].show()

    def _reset_plots(self):
        """ Resets single scan traces """

        for index, plot in enumerate(self.iplot_fwd):
            plot.set_data(x_ar=np.array([]), y_ar=np.array([]))
            if self.sweep_type != 'sawtooth':
                self.iplot_bwd[index].set_data(x_ar=np.array([]), y_ar=np.array([]))

    def _run_and_plot(self, x_value, backward=False):
        """ Runs the experiment for an x value and adds to plot

        :param x_value: (double) experiment parameter
        :param backward: (bool) whether or not backward or forward
        """

        y_values = self.run_once(x_value)
        for index, y_value in enumerate(y_values):
            if backward:
                self.iplot_bwd[index].append_data(x_ar=x_value, y_ar=y_value, ind=0)
            else:
                self.iplot_fwd[index].append_data(x_ar=x_value, y_ar=y_value, ind=0)

    def _update_hmaps(self, reps_done):
        """ Updates heat map plots

        :param reps_done: (int) number of repetitions done
        """

        for index, fwd_plot in enumerate(self.iplot_fwd):

            if reps_done == 1:
                self.hplot_fwd[index].set_data(
                    y_ar=np.array([1]),
                    z_ar=[fwd_plot._y_ar]
                )
                if self.sweep_type != 'sawtooth':
                    self.hplot_bwd[index].set_data(
                        y_ar=np.array([1]),
                        z_ar=[self.iplot_bwd[index]._y_ar]
                    )
            else:
                self.hplot_fwd[index].append_row(
                    y_val=reps_done,
                    z_ar=fwd_plot._fig.data[0].y
                )
                if self.sweep_type != 'sawtooth':
                    self.hplot_bwd[index].append_row(
                        y_val=reps_done,
                        z_ar=self.iplot_bwd[index]._fig.data[0].y
                    )

    def _update_integrated(self, reps_done):
        """ Updates integrated plots

        :param reps_done: (int) number of repetitions completed
        """

        for index, fwd_plot in enumerate(self.iplot_fwd):

            if reps_done==1:
                fwd_plot.set_data(
                    x_ar=np.linspace(self.min, self.max, self.pts),
                    y_ar=fwd_plot._fig.data[0].y,
                    ind=1
                )
                if self.sweep_type != 'sawtooth':
                    self.iplot_bwd[index].set_data(
                        x_ar=np.linspace(self.max, self.min, self.pts),
                        y_ar=self.iplot_bwd[index]._fig.data[0].y,
                        ind=1
                    )

            else:
                fwd_plot.set_data(
                    x_ar=np.linspace(self.min, self.max, self.pts),
                    y_ar=((fwd_plot._fig.data[1].y*(reps_done-1)/reps_done)
                        +fwd_plot._fig.data[0].y/reps_done),
                    ind=1
                )

                if self.sweep_type != 'sawtooth':
                    self.iplot_bwd[index].set_data(
                        x_ar=np.linspace(self.max, self.min, self.pts),
                        y_ar=((self.iplot_bwd[index]._fig.data[1].y*(reps_done-1)/reps_done)
                            +self.iplot_bwd[index]._fig.data[0].y/reps_done),
                        ind=1
                    )
